import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage, Image
from control_msgs.action import GripperCommand
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import JointState
from cv_bridge import CvBridge
from pymoveit2 import MoveIt2
import numpy as np
import cv2
import ncnn
import time
import math
import threading
import psutil
import requests
from enum import Enum


class State(Enum):
    SEARCH        = 'SEARCH'
    ALIGN         = 'ALIGN'
    CHECK_DEPTH   = 'CHECK_DEPTH'
    QUALITY_CHECK = 'QUALITY_CHECK'
    HARVEST       = 'HARVEST'
    SORT          = 'SORT'
    DONE          = 'DONE'


SCRIPTS_DIR = '/home/ubuntu24'
PARAM_PATH  = f'{SCRIPTS_DIR}/model.ncnn.param'
BIN_PATH    = f'{SCRIPTS_DIR}/model.ncnn.bin'

IMGSZ       = 416
CONF_THRESH = 0.65
IOU_THRESH  = 0.3
CLASSES     = ['fresh', 'rotten', 'surface_damage', 'unripe']
SKIP_GRADES = {'D', 'U'}

SEARCH_SPEED     = 0.03
ALIGN_SPEED      = 0.02
ALIGN_THRESHOLD  = 80
TARGET_DEPTH_MIN = 0.2
TARGET_DEPTH_MAX = 0.6
FRAME_SKIP       = 10

# ★ 변경: 좌표 측정 안정화 파라미터
SETTLE_TIME      = 0.5    # 정지 후 측정 시작까지 대기 (관성/프레임 지연 흡수)
DEPTH_SAMPLES_N  = 5      # 3D 좌표 샘플 개수
DEPTH_STD_MAX    = 0.01   # 샘플 표준편차 허용치 (1cm 넘게 흔들리면 재수집)

# ★ 변경: 2단계 접근 (pre-grasp 오프셋, 베이스 X축 기준 뒤쪽)
APPROACH_OFFSET  = 0.15

# ★ 변경: 작업공간 한계 — 실제 팔 스펙에 맞게 조정할 것!
WS_R_MIN, WS_R_MAX = 0.10, 0.45   # 수평거리 sqrt(x^2+y^2)
WS_Z_MIN, WS_Z_MAX = 0.02, 0.35   # 높이

ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
ARUCO_DETECTOR = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)

FX = 619.33
FY = 619.65
CX = 328.74
CY = 249.07

# DB 서버 URL
HARVEST_API_URL = "http://10.10.16.17:8000/robot/harvest"

# 등급 매핑
GRADE_MAP = {'A': '상', 'B': '중', 'C': '하'}
SIZE_MAP  = {'L': '대', 'S': '중'}

HOME_POSITION = [0.0, -1.57, 1.17, 1.57, 0.0]
VIA_POSITION  = [0.0, -1.0, 0.8, 1.0, 0.0]
BOX_POSITION = {
    'A': [0.7823884515789565, -0.23009711818305334, 0.5691068723053658, 1.1152040327926542, -1.0538448012776422],
    'B': [0.48,-0.23,0.57,1.4,-1.05],
    'C': [-0.08,-0.23,0.57,1.4,-1.05],
    'U': [-0.48,-0.23,0.57,1.2,-1.05],
    'D': [-0.88,-0.23,0.57,1.2,-1.05],
}

QOS_BEST_EFFORT = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1)


def preprocess(frame, imgsz):
    h, w = frame.shape[:2]
    scale = min(imgsz/w, imgsz/h)
    nw, nh = int(w*scale), int(h*scale)
    resized = cv2.resize(frame, (nw, nh))
    padded = np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)
    pad_x = (imgsz-nw)//2
    pad_y = (imgsz-nh)//2
    padded[pad_y:pad_y+nh, pad_x:pad_x+nw] = resized
    return padded, scale, pad_x, pad_y


def postprocess(output, conf_thresh, iou_thresh, scale, pad_x, pad_y, orig_w, orig_h):
    output = np.array(output)
    if output.ndim == 2:
        if output.shape[0] < output.shape[1]:
            output = output.T
    elif output.ndim == 3:
        output = output[0]
        if output.shape[0] < output.shape[1]:
            output = output.T

    boxes, scores, class_ids, all_scores = [], [], [], []
    for det in output:
        cls_scores = det[4:]
        cls_id = int(np.argmax(cls_scores))
        conf = float(cls_scores[cls_id])
        if conf < conf_thresh:
            continue
        cx, cy, bw, bh = det[0], det[1], det[2], det[3]
        x1 = max(0.0, (cx-bw/2-pad_x)/scale)
        y1 = max(0.0, (cy-bh/2-pad_y)/scale)
        x2 = min(orig_w, (cx+bw/2-pad_x)/scale)
        y2 = min(orig_h, (cy+bh/2-pad_y)/scale)
        boxes.append([x1, y1, x2-x1, y2-y1])
        scores.append(conf)
        class_ids.append(cls_id)
        all_scores.append(cls_scores.tolist())

    if not boxes:
        return []

    indices = cv2.dnn.NMSBoxes(boxes, scores, conf_thresh, iou_thresh)
    results = []
    for i in indices:
        idx = i[0] if isinstance(i, (list, tuple, np.ndarray)) else i
        x, y, w, h = boxes[idx]
        results.append({
            'bbox':       [x, y, x+w, y+h],
            'conf':       scores[idx],
            'class':      class_ids[idx],
            'label':      CLASSES[class_ids[idx]],
            'all_scores': all_scores[idx],
            'cx':         int(x+w/2),
            'cy':         int(y+h/2),
        })
    return results


def determine_grade(all_scores):
    fresh_score  = all_scores[0]
    rotten_score = all_scores[1]
    damage_score = all_scores[2]
    unripe_score = all_scores[3]

    if rotten_score > 0.5:
        return 'D', fresh_score - damage_score
    if unripe_score > 0.5:
        return 'U', fresh_score - damage_score

    quality = fresh_score - damage_score
    if   quality > 0.6: grade = 'A'
    elif quality > 0.3: grade = 'B'
    elif quality > 0.0: grade = 'C'
    else: grade = 'D'

    return grade, quality


def determine_size(bbox, depth_m):
    x1, y1, x2, y2 = bbox
    pixel_w = x2 - x1
    pixel_h = y2 - y1
    pixel_size = max(pixel_w, pixel_h)
    real_size_cm = (pixel_size * depth_m / 619.33) * 100
    size = 'S' if real_size_cm <= 2.5 else 'L'
    return size, real_size_cm


def send_harvest_data(grade, size, logger):
    """수확 데이터를 DB 서버로 전송"""
    quality_grade = GRADE_MAP.get(grade)
    size_class    = SIZE_MAP.get(size)

    if quality_grade is None or size_class is None:
        logger.warn(f'[API] 전송 스킵 - 매핑 없음 grade={grade} size={size}')
        return

    payload = {
        'size_class':    size_class,
        'quality_grade': quality_grade,
    }
    try:
        response = requests.post(HARVEST_API_URL, json=payload, timeout=3)
        logger.info(f'[API] 전송 완료 → {payload} | status={response.status_code} | {response.json()}')
    except Exception as e:
        logger.error(f'[API] 전송 실패: {e}')


class AppleHarvester(Node):

    def __init__(self):
        super().__init__('apple_harvester')
        self.bridge         = CvBridge()
        self.callback_group = ReentrantCallbackGroup()
        self._detect_lock   = threading.Lock()

        self._display_frame = None
        self._display_lock  = threading.Lock()
        self._running       = True

        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = False
        self.net.opt.num_threads = 4
        self.net.load_param(PARAM_PATH)
        self.net.load_model(BIN_PATH)
        self.get_logger().info('[INIT] NCNN 로딩 완료 ✓')

        # ★ 변경: 사용하지 않던 SingleThreadedExecutor 제거 (MultiThreadedExecutor 하나로 통일)
        self.moveit2 = MoveIt2(
            node=self,
            joint_names=['joint1','joint2','joint3','joint4','joint5'],
            base_link_name='link0',
            end_effector_name='end_effector_link',
            group_name='arm',
            callback_group=self.callback_group,
            execute_via_moveit=True,
        )
        self.moveit2.planner_id       = 'RRTConnectkConfigDefault'
        self.moveit2.max_velocity     = 0.3
        self.moveit2.max_acceleration = 0.3
        # ★ 변경: start state 불일치로 인한 abort 완화 (0.05 → 0.1)
        self.moveit2.allowed_start_tolerance = 0.1

        self.state         = State.SEARCH
        self.apple_3d_pos  = None
        self.current_grade = None
        self.current_size  = None
        self.depth_image   = None
        self._last_frame   = None
        self._last_detections = []
        self._skip_count   = 0
        self._frame_count  = 0
        self._last_fps_time = time.time()
        self.IMG_W = 640
        self.IMG_H = 480

        # ★ 변경: 다중 프레임 3D 좌표 샘플링용
        self._depth_samples = []
        self._settle_until  = None

        self._last_joint_positions = None
        self.cmd_vel_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.gripper_client = ActionClient(
            self, GripperCommand, '/gripper_controller/gripper_cmd')

        self.create_subscription(
            JointState,
            '/joint_states',
            self._joint_state_callback, 10,
            callback_group=self.callback_group)
        self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.color_callback, QOS_BEST_EFFORT,
            callback_group=self.callback_group)
        self.create_subscription(
            Image,
            '/camera/camera/depth/image_rect_raw',
            self.depth_callback, QOS_BEST_EFFORT,
            callback_group=self.callback_group)

        self.create_timer(5.0, self.monitor_resources)
        self.gripper_client.wait_for_server()

        self._display_thread = threading.Thread(
            target=self._display_loop, daemon=True)
        self._display_thread.start()

        self.get_logger().info(f'[INIT] 초기화 완료 — 상태: {self.state.value}')

    def _display_loop(self):
        cv2.namedWindow('Apple Harvester', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Apple Harvester', 800, 600)
        while self._running:
            with self._display_lock:
                frame = self._display_frame.copy() if self._display_frame is not None else None
            if frame is not None:
                cv2.imshow('Apple Harvester', frame)
            key = cv2.waitKey(30)
            if key == ord('q'):
                self.get_logger().info('[DISPLAY] q 키 입력 → 창 닫기')
                break
        cv2.destroyAllWindows()

    def monitor_resources(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        now = time.time()
        fps = self._frame_count / max(now - self._last_fps_time, 0.001)
        self._frame_count   = 0
        self._last_fps_time = now
        self.get_logger().info(
            f'[MONITOR] CPU:{cpu:.0f}% MEM:{mem:.0f}% '
            f'FPS:{fps:.1f} 상태:{self.state.value}')

    def _joint_state_callback(self, msg):
        try:
            idx = [msg.name.index(j) for j in ['joint1','joint2','joint3','joint4','joint5']]
            self._last_joint_positions = [msg.position[i] for i in idx]
        except:
            pass

    def depth_callback(self, msg):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(
                msg, desired_encoding='passthrough')
        except Exception as e:
            self.get_logger().error(f'[DEPTH] 변환 실패: {e}')

    def pixel_to_3d(self, u, v, depth_m):
        X_cam = (u - CX) * depth_m / FX
        Y_cam = (v - CY) * depth_m / FY
        Z_cam = depth_m
        X_base = Z_cam + 0.03
        Y_base = -X_cam + 0.05
        Z_base = -Y_cam + 0.10
        return X_base, Y_base, Z_base

    def detect_apples(self, frame):
        with self._detect_lock:
            try:
                orig_h, orig_w = frame.shape[:2]
                padded, scale, pad_x, pad_y = preprocess(frame, IMGSZ)
                rgb    = padded[:, :, ::-1].copy()
                mat_in = ncnn.Mat.from_pixels(
                    rgb, ncnn.Mat.PixelType.PIXEL_RGB, IMGSZ, IMGSZ)
                mat_in.substract_mean_normalize([0.0]*3, [1/255.0]*3)
                ex = self.net.create_extractor()
                ex.input('in0', mat_in)
                _, mat_out = ex.extract('out0')
                return postprocess(mat_out, CONF_THRESH, IOU_THRESH,
                                   scale, pad_x, pad_y, orig_w, orig_h)
            except Exception as e:
                self.get_logger().error(f'[DETECT] 오류: {e}')
                return []

    # ★ 변경: bbox 중앙 40% 영역만 사용 (배경 픽셀 오염 방지)
    def get_3d_from_bbox(self, x1, y1, x2, y2):
        if self.depth_image is None:
            return None
        w = x2 - x1
        h = y2 - y1
        cx1 = x1 + int(w * 0.3)
        cx2 = x2 - int(w * 0.3)
        cy1 = y1 + int(h * 0.3)
        cy2 = y2 - int(h * 0.3)
        if cx2 <= cx1 or cy2 <= cy1:   # bbox가 너무 작으면 원본 사용
            cx1, cy1, cx2, cy2 = x1, y1, x2, y2
        H, W = self.depth_image.shape[:2]
        roi = self.depth_image[
            max(0,cy1):min(H,cy2),
            max(0,cx1):min(W,cx2)
        ].astype(float)
        if roi.size == 0:
            return None
        roi[roi==0] = np.nan
        if np.isnan(roi).all():
            return None
        depth_m = float(np.nanmedian(roi)) * 0.001
        u = (x1+x2)//2
        v = (y1+y2)//2
        return self.pixel_to_3d(u, v, depth_m)

    # ★ 변경: 샘플링 상태 초기화 헬퍼
    def _reset_depth_sampling(self):
        self._depth_samples = []
        self._settle_until  = None

    # ★ 변경: wait_until_executed 결과 확인 + 재시도, tolerance 점진 완화
    def move_to_pose(self, x, y, z, retries=3):
        for attempt in range(1, retries + 1):
            tol = 0.05 + (attempt - 1) * 0.02
            self.get_logger().info(
                f'[MOVEIT] 포즈이동 x={x:.3f} y={y:.3f} z={z:.3f} '
                f'(시도 {attempt}/{retries}, tol={tol:.2f})')
            time.sleep(0.5)
            self.moveit2.move_to_pose(
                position=[x, y, z],
                quat_xyzw=[0.0, 0.0, 0.0, 1.0],
                tolerance_position=tol,
                tolerance_orientation=6.28,
            )
            result = self.moveit2.wait_until_executed()
            # 구버전 pymoveit2는 None 반환 → 성공으로 간주 (기존 동작 유지)
            ok = True if result is None else bool(result)
            if ok:
                time.sleep(0.5)
                return True
            self.get_logger().warn(f'[MOVEIT] 포즈이동 실패 (시도 {attempt}/{retries})')
            time.sleep(1.0)
        return False

    # ★ 변경: 관절이동도 결과 확인 + 재시도
    def move_to_joints(self, positions, retries=2):
        for attempt in range(1, retries + 1):
            self.get_logger().info(
                f'[MOVEIT] 관절이동 {positions} (시도 {attempt}/{retries})')
            time.sleep(0.5)
            self.moveit2.move_to_configuration(positions)
            result = self.moveit2.wait_until_executed()
            ok = True if result is None else bool(result)
            if ok:
                time.sleep(0.5)
                return True
            self.get_logger().warn(f'[MOVEIT] 관절이동 실패 (시도 {attempt}/{retries})')
            time.sleep(1.0)
        return False

    def move_to_home(self):
        self.get_logger().info('[MOVEIT] 홈 복귀')
        return self.move_to_joints(HOME_POSITION)

    # ★ 변경: MoveIt 전부 실패 시 최후 수단 (joint_trajectory 직접 publish)
    def force_home(self):
        self.get_logger().warn('[MOVEIT] 강제 홈 복귀 (joint_trajectory 직접 발행)')
        import subprocess
        subprocess.Popen(['ros2', 'topic', 'pub', '--once',
            '/arm_controller/joint_trajectory',
            'trajectory_msgs/msg/JointTrajectory',
            '{joint_names: [joint1,joint2,joint3,joint4,joint5], points: [{positions: [0.0,-1.57,1.17,1.57,0.0], time_from_start: {sec: 3}}]}'])
        time.sleep(6.0)

    def move_robot(self, linear=0.0, angular=0.0):
        twist = TwistStamped()
        twist.header.stamp    = self.get_clock().now().to_msg()
        twist.twist.linear.x  = linear
        twist.twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)

    # ★ 변경: 정지 명령 여러 번 발행 (관성/유실 대비)
    def stop_robot(self):
        twist = TwistStamped()
        for _ in range(5):
            twist.header.stamp = self.get_clock().now().to_msg()
            self.cmd_vel_pub.publish(twist)
            time.sleep(0.02)

    def gripper_move(self, position):
        goal = GripperCommand.Goal()
        goal.command.position   = position
        goal.command.max_effort = 10.0
        self.gripper_client.send_goal_async(goal)
        self.get_logger().info(f'[GRIPPER] → {position}')

    def color_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            if frame is None:
                return
            self._last_frame = frame
        except Exception as e:
            self.get_logger().error(f'[COLOR] 변환 실패: {e}')
            return

        display = frame.copy()
        for det in self._last_detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            grade, _ = determine_grade(det['all_scores'])
            color = {
                'A': (0,255,0),
                'B': (0,255,255),
                'C': (0,165,255),
                'U': (255,165,0),
                'D': (0,0,255)
            }.get(grade, (255,255,255))
            cv2.rectangle(display, (x1,y1), (x2,y2), color, 2)
            cv2.putText(display,
                f'{det["label"]} {grade} {det["conf"]:.2f}',
                (x1, y1-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.putText(display, f'State: {self.state.value}',
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)

        with self._display_lock:
            self._display_frame = display

        self._frame_count += 1

        if self.state in (State.HARVEST, State.SORT, State.DONE):
            return

        self._skip_count += 1
        if self._skip_count % FRAME_SKIP != 0:
            return

        try:
            detections = self.detect_apples(frame)
            self._last_detections = detections
        except Exception:
            return

        # ── SEARCH ──
        if self.state == State.SEARCH:
            # 검출된 것 중 rotten/unripe를 뺀 '수확 가능' 사과만 추림
            harvestable = [d for d in detections
                           if determine_grade(d['all_scores'])[0] not in SKIP_GRADES]
            if not harvestable:
                # 사과가 없거나, 있어도 전부 rotten/unripe → 다음 나무로 계속 전진
                self.move_robot(linear=SEARCH_SPEED)
            else:
                self.get_logger().info(
                    f'[SEARCH] 수확 가능 사과 {len(harvestable)}개 발견 → ALIGN')
                self.stop_robot()
                self.state = State.ALIGN

        #if self.state == State.SEARCH:
        #    if not detections:
        #        self.move_robot(linear=SEARCH_SPEED)
        #    else:
        #        self.get_logger().info('[SEARCH] 사과 발견 → ALIGN')
        #        self.stop_robot()
        #        self.state = State.ALIGN

        # ── ALIGN ──
        elif self.state == State.ALIGN:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = ARUCO_DETECTOR.detectMarkers(gray)
            if ids is None or not any(i[0] in [0,1] for i in ids):
                self.move_robot(linear=SEARCH_SPEED)
                return
            cx_marker = int(np.mean([corners[i][0][:,0].mean()
                for i, mid in enumerate(ids) if mid[0] in [0,1]]))
            error = cx_marker - self.IMG_W // 2
            self.get_logger().info(f'[ALIGN] ArUco ID={[i[0] for i in ids]} cx={cx_marker} error={error}')
            if abs(error) <= ALIGN_THRESHOLD:
                self.stop_robot()
                self.get_logger().info('[ALIGN] 정렬 완료 → CHECK_DEPTH')
                self._reset_depth_sampling()
                self.state = State.CHECK_DEPTH
            elif error < 0:
                self.move_robot(linear=ALIGN_SPEED)
            else:
                self.move_robot(linear=-ALIGN_SPEED)

        # ── CHECK_DEPTH ──
        # ★ 변경: 정지 → 안정화 대기 → 다중 프레임 샘플링 → 표준편차 검증 → 중앙값 확정
        elif self.state == State.CHECK_DEPTH:
            if not detections or self.depth_image is None:
                self._reset_depth_sampling()
                self.state = State.SEARCH
                return
            det = detections[0]
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            pos = self.get_3d_from_bbox(x1, y1, x2, y2)
            if pos is None:
                self._reset_depth_sampling()
                self.state = State.SEARCH
                return
            X, Y, Z = pos
            depth_m = X - 0.08

            if depth_m < TARGET_DEPTH_MIN:
                self._reset_depth_sampling()
                self.move_robot(linear=-ALIGN_SPEED)
                return
            elif depth_m > TARGET_DEPTH_MAX:
                self._reset_depth_sampling()
                self.move_robot(linear=ALIGN_SPEED)
                return

            # 거리 범위 안 → 정지 후 안정화 대기
            if self._settle_until is None:
                self.stop_robot()
                self._settle_until = time.time() + SETTLE_TIME
                self.get_logger().info(f'[DEPTH] 정지 → {SETTLE_TIME}s 안정화 대기')
                return
            if time.time() < self._settle_until:
                return

            # 샘플 수집
            self._depth_samples.append(pos)
            self.get_logger().info(
                f'[DEPTH] 샘플 {len(self._depth_samples)}/{DEPTH_SAMPLES_N} '
                f'x={X:.3f} y={Y:.3f} z={Z:.3f}')
            if len(self._depth_samples) < DEPTH_SAMPLES_N:
                return

            arr = np.array(self._depth_samples)
            std_max = float(np.max(np.std(arr, axis=0)))
            if std_max > DEPTH_STD_MAX:
                self.get_logger().warn(
                    f'[DEPTH] 측정 불안정 std={std_max*1000:.1f}mm → 재수집')
                self._depth_samples = []
                return

            fx, fy, fz = np.median(arr, axis=0)
            self.apple_3d_pos = (float(fx), float(fy), float(fz))
            self.get_logger().info(
                f'[DEPTH] 좌표 확정 ✓ x={fx:.3f} y={fy:.3f} z={fz:.3f} '
                f'(std={std_max*1000:.1f}mm)')
            self._reset_depth_sampling()
            self.state = State.QUALITY_CHECK

        # ── QUALITY_CHECK ──
        elif self.state == State.QUALITY_CHECK:
            if not detections:
                self.state = State.SEARCH
                return
            # 각 박스의 병합 점수 계산 (박스 안에 damage/rotten 박스 포함 시 반영)
            def merged_scores(cand):
                scores = list(cand['all_scores'])
                x1, y1, x2, y2 = cand['bbox']
                for det in detections:
                    if det is not cand and x1 <= det['cx'] <= x2 and y1 <= det['cy'] <= y2:
                        for i in range(4):
                            scores[i] = max(scores[i], det['all_scores'][i])
                return scores
            # D등급 사과는 맨 뒤로 정렬 → D 아닌 사과 우선 선택
            detections.sort(key=lambda d: determine_grade(merged_scores(d))[0] in SKIP_GRADES)
            all_scores = merged_scores(detections[0])
            grade, quality = determine_grade(all_scores)
            # 선택된 사과 기준 3D 좌표 재계산
            sx1, sy1, sx2, sy2 = [int(v) for v in detections[0]['bbox']]
            new_pos = self.get_3d_from_bbox(sx1, sy1, sx2, sy2)
            if new_pos is not None:
                self.apple_3d_pos = new_pos
            bbox = detections[0]['bbox']
            X, Y, Z = self.apple_3d_pos
            depth_m = X - 0.08
            size, size_cm = determine_size(bbox, depth_m)
            x1, y1, x2, y2 = bbox
            pixel_w = int(x2 - x1)
            pixel_h = int(y2 - y1)
            self.get_logger().info(
                f'[QUALITY] 등급={grade} 점수={quality:.2f} 크기={size}({size_cm:.1f}cm) '
                f'픽셀={pixel_w}x{pixel_h} depth={depth_m:.3f}m '
                f'fresh={all_scores[0]:.2f} rotten={all_scores[1]:.2f} '
                f'damage={all_scores[2]:.2f} unripe={all_scores[3]:.2f}')
            if grade in SKIP_GRADES:
                self.get_logger().info(f'[QUALITY] {grade}등급(skip) → 무시하고 재탐색')
                self.state = State.SEARCH
                return
            if size_cm > 4.5:
                self.get_logger().info(f'[QUALITY] 크기 {size_cm:.1f}cm > 4.5cm → 사과 아님 스킵')
                self.state = State.SEARCH
                return

            self.get_logger().info(
                f'[QUALITY] 수확 결정 → 등급={grade}({quality:.2f}점) 크기={size}({size_cm:.1f}cm) '
                f'x={X:.3f} y={Y:.3f} z={Z:.3f}')

            self.current_grade = grade
            self.current_size  = size
            self.state = State.HARVEST
            threading.Thread(
                target=self._harvest_thread,
                daemon=True).start()

    def _harvest_thread(self):
        def log(msg): self.get_logger().info(msg)
        harvested = False
        try:
            X, Y, Z = self.apple_3d_pos
            grade = self.current_grade
            size  = self.current_size

            # ★ 변경: 작업공간 사전 검증 — 못 가는 좌표는 시도조차 안 함 (abort 예방)
            r = math.hypot(X, Y)
            if not (WS_R_MIN < r < WS_R_MAX and WS_Z_MIN < Z < WS_Z_MAX):
                self.get_logger().warn(
                    f'[HARVEST] 작업공간 밖 r={r:.3f} z={Z:.3f} '
                    f'(허용 r:{WS_R_MIN}~{WS_R_MAX}, z:{WS_Z_MIN}~{WS_Z_MAX}) → 스킵')
                return

            log(f'[HARVEST] 시작 등급={grade} 크기={size} x={X:.3f} y={Y:.3f} z={Z:.3f}')

            log('[HARVEST] 그리퍼 열기')
            self.gripper_move(0.5)
            time.sleep(1.0)

            # ★ 변경: 2단계 접근 — pre-grasp 지점 먼저, 그 다음 최종 접근
            log(f'[HARVEST] 1차 접근 (pre-grasp) X:{X-APPROACH_OFFSET:.3f} Y:{Y:.3f} Z:{Z:.3f}')
            if not self.move_to_pose(X - APPROACH_OFFSET, Y, Z):
                self.get_logger().warn('[HARVEST] 1차 접근 실패 → 홈 복귀 후 재탐색')
                if not self.move_to_home():
                    self.force_home()
                return

            log(f'[HARVEST] 최종 접근 X:{X:.3f} Y:{Y:.3f} Z:{Z:.3f}')
            if not self.move_to_pose(X, Y, Z):
                self.get_logger().warn('[HARVEST] 최종 접근 실패 → 홈 복귀 후 재탐색')
                if not self.move_to_home():
                    self.force_home()
                return

            log('[HARVEST] 그리퍼 닫기')
            self.gripper_move(0.0)
            time.sleep(1.0)

            log('[HARVEST] 홈 경유')
            if not self.move_to_joints(VIA_POSITION):
                self.get_logger().warn('[HARVEST] 경유점 이동 실패 → 그리퍼 열고 복귀')
                self.gripper_move(1.1)
                time.sleep(1.0)
                if not self.move_to_home():
                    self.force_home()
                return

            self.state = State.SORT
            log(f'[SORT] 등급={grade} 박스로 이동')
            if not self.move_to_joints(BOX_POSITION[grade]):
                self.get_logger().warn('[SORT] 박스 이동 실패 → 현 위치에서 그리퍼 열기')
                # 박스까지 못 가면 일단 놓고 복귀 (사과 들고 멈춰있는 것 방지)
                self.gripper_move(1.1)
                time.sleep(1.5)
                if not self.move_to_home():
                    self.force_home()
                return

            log('[SORT] 그리퍼 열기')
            self.gripper_move(1.1)
            time.sleep(1.5)
            harvested = True

            # 수확 완료 후 DB 전송
            send_harvest_data(grade, size, self.get_logger())

            log('[SORT] 홈 복귀')
            if not self.move_to_home():
                self.force_home()

            self.state = State.DONE
            log(f'[DONE] 수확 완료 ✓ 등급={grade} 크기={size}')

        except Exception as e:
            self.get_logger().error(f'[HARVEST] 오류: {e}')
            import traceback
            self.get_logger().error(traceback.format_exc())
            self.force_home()
        finally:
            self.get_logger().info('[HARVEST] 스레드 종료 → 상태 초기화')
            if not harvested:
                try:
                    self.gripper_move(1.1)
                except:
                    pass
            self._last_detections = []
            self.apple_3d_pos  = None
            self.current_grade = None
            self.current_size  = None
            self._reset_depth_sampling()
            self.state = State.SEARCH
            self.get_logger().info('[SEARCH] 다음 사과 탐색 시작')


def main():
    rclpy.init()
    node = AppleHarvester()
    executor = rclpy.executors.MultiThreadedExecutor(8)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('[SHUTDOWN] 종료')
    finally:
        node._running = False
        twist = TwistStamped()
        twist.header.stamp = node.get_clock().now().to_msg()
        node.cmd_vel_pub.publish(twist)
        time.sleep(0.5)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

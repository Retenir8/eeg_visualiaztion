#!/bin/bash

# 脑机接口系统测试脚本
# 用于测试系统的各个组件

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# 测试配置加载
test_config_loading() {
    log_test "测试配置加载功能..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import yaml
import sys

try:
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print('配置文件加载成功')
    
    # 检查必要配置项
    required_keys = ['openbci', 'signal_processing', 'communication', 'logging']
    for key in required_keys:
        if key in config:
            print(f'配置项 {key} 存在')
        else:
            print(f'警告: 缺少配置项 {key}')
    
except Exception as e:
    print(f'配置加载失败: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "配置加载测试通过"
    else
        log_error "配置加载测试失败"
        return 1
    fi
}

# 测试数据采集模块
test_data_acquisition() {
    log_test "测试数据采集模块..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import sys
sys.path.append('.')

try:
    from data_acquisition.openbci_interface import OpenBCISimulator
    
    # 创建模拟器
    simulator = OpenBCISimulator(sample_rate=250, num_channels=8)
    print('OpenBCI模拟器创建成功')
    
    # 测试设备信息
    info = simulator.get_device_info()
    print(f'设备信息: {info}')
    
    # 测试连接
    if simulator.connect():
        print('设备连接成功')
        
        # 测试数据生成
        sample = simulator._generate_sample()
        print(f'生成样本: {len(sample)} 通道')
        print(f'样本数据: {[f\"{x:.2f}\" for x in sample[:3]]}...')
        
        simulator.disconnect()
        print('设备断开连接')
    else:
        print('设备连接失败')
        
except Exception as e:
    print(f'数据采集测试失败: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "数据采集模块测试通过"
    else
        log_error "数据采集模块测试失败"
        return 1
    fi
}

# 测试信号处理模块
test_signal_processing() {
    log_test "测试信号处理模块..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import sys
import numpy as np
sys.path.append('.')

try:
    from signal_processing.preprocessor import EEGPreprocessor
    from signal_processing.feature_extractor import FeatureExtractor
    
    # 创建测试数据
    sample_rate = 250
    duration = 2.0  # 2秒
    samples = int(duration * sample_rate)
    channels = 8
    
    # 生成模拟EEG数据
    t = np.linspace(0, duration, samples)
    test_data = np.zeros((samples, channels))
    
    # 添加不同频率的成分
    frequencies = [10, 20, 30, 40, 25, 15, 35, 45]
    for i in range(channels):
        test_data[:, i] = np.sin(2 * np.pi * frequencies[i] * t) * 50
    
    print(f'生成测试数据: {test_data.shape}')
    
    # 测试预处理器
    preprocessor = EEGPreprocessor(sample_rate)
    print('EEG预处理器创建成功')
    
    filtered_data = preprocessor.apply_all_filters(test_data)
    print(f'滤波后数据形状: {filtered_data.shape}')
    
    # 测试特征提取器
    extractor = FeatureExtractor(sample_rate)
    print('特征提取器创建成功')
    
    features = extractor.extract_all_features(filtered_data[:256])  # 取前256个样本
    print(f'提取特征: {len(features)} 类特征')
    
    for category, category_features in features.items():
        if isinstance(category_features, dict):
            print(f'{category}: {len(category_features)} 个特征')
    
except Exception as e:
    print(f'信号处理测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "信号处理模块测试通过"
    else
        log_error "信号处理模块测试失败"
        return 1
    fi
}

# 测试通信模块
test_communication() {
    log_test "测试通信模块..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import sys
import json
import time
sys.path.append('.')

try:
    from communication.data_serializer import DataSerializer
    
    # 创建序列化器
    serializer = DataSerializer()
    print('数据序列化器创建成功')
    
    # 测试EEG数据序列化
    import numpy as np
    eeg_data = np.random.randn(100, 8)
    metadata = {'sample_rate': 250, 'channels': 8}
    
    serialized = serializer.serialize_eeg_data(eeg_data, metadata)
    print(f'EEG数据序列化成功，长度: {len(serialized)}')
    
    # 测试反序列化
    deserialized_data, deserialized_metadata = serializer.deserialize_eeg_data(serialized)
    print(f'EEG数据反序列化成功，形状: {deserialized_data.shape}')
    
    # 测试特征序列化
    features = {
        'time_domain': {'mean': 1.0, 'std': 2.0},
        'frequency_bands': {'alpha': 10.0, 'beta': 20.0}
    }
    
    serialized_features = serializer.serialize_features(features)
    print(f'特征序列化成功，长度: {len(serialized_features)}')
    
    # 测试反序列化
    deserialized_features, _ = serializer.deserialize_features(serialized_features)
    print(f'特征反序列化成功: {deserialized_features}')
    
except Exception as e:
    print(f'通信模块测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "通信模块测试通过"
    else
        log_error "通信模块测试失败"
        return 1
    fi
}

# 测试UDP通信（可选）
test_udp_communication() {
    log_test "测试UDP通信..."
    
    cd "$SERVER_DIR"
    
    # 这里可以添加UDP通信的测试
    # 由于UDP需要网络环境，暂时跳过
    
    log_warn "UDP通信测试需要网络环境，跳过"
    log_info "UDP通信测试通过（跳过）"
}

# 测试工具模块
test_utils() {
    log_test "测试工具模块..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import sys
import numpy as np
sys.path.append('.')

try:
    from utils.logger import Logger
    from utils.validator import DataValidator
    
    # 测试日志器
    logger = Logger('TestLogger', 'INFO')
    logger.info('测试日志记录')
    print('日志器测试成功')
    
    # 测试数据验证器
    validator = DataValidator()
    
    # 创建测试数据
    test_data = np.random.randn(10, 8)
    
    # 测试各种验证功能
    is_valid = validator.validate_eeg_channels(test_data, 8)
    print(f'EEG通道验证: {is_valid}')
    
    artifacts = validator.detect_artifacts(test_data, threshold=3.0)
    print(f'检测到伪迹: {len(artifacts)} 个')
    
    frequency_band_valid = validator.validate_frequency_band('alpha')
    print(f'频带验证: {frequency_band_valid}')
    
except Exception as e:
    print(f'工具模块测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "工具模块测试通过"
    else
        log_error "工具模块测试失败"
        return 1
    fi
}

# 集成测试
test_integration() {
    log_test "执行集成测试..."
    
    cd "$SERVER_DIR"
    
    python3 -c "
import sys
import time
sys.path.append('.')

try:
    print('开始集成测试...')
    
    # 模拟完整的数据流
    from data_acquisition.openbci_interface import OpenBCISimulator
    from signal_processing.preprocessor import EEGPreprocessor
    from signal_processing.feature_extractor import RealTimeFeatureExtractor
    from communication.data_serializer import DataSerializer
    
    # 创建组件
    simulator = OpenBCISimulator(sample_rate=250, num_channels=8)
    preprocessor = EEGPreprocessor(250)
    feature_extractor = RealTimeFeatureExtractor(250, 256)
    serializer = DataSerializer()
    
    print('所有组件创建成功')
    
    # 模拟数据流
    simulator.connect()
    
    # 获取10个样本进行测试
    samples_processed = 0
    for i in range(10):
        # 生成样本
        sample_data = simulator._generate_sample()
        timestamp = time.time()
        
        # 预处理
        sample_array = np.array(sample_data).reshape(1, -1)
        filtered_sample = preprocessor.apply_all_filters(sample_array)[0]
        
        # 特征提取
        features = feature_extractor.process_sample(filtered_sample.tolist(), timestamp)
        
        if features:
            samples_processed += 1
        
        time.sleep(0.01)  # 模拟真实时间间隔
    
    simulator.disconnect()
    
    print(f'集成测试完成，处理 {samples_processed} 个样本')
    
except Exception as e:
    print(f'集成测试失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "集成测试通过"
    else
        log_error "集成测试失败"
        return 1
    fi
}

# 运行所有测试
run_all_tests() {
    log_info "开始运行系统测试..."
    echo ""
    
    local failed_tests=0
    
    # 测试模块
    test_config_loading || ((failed_tests++))
    echo ""
    
    test_data_acquisition || ((failed_tests++))
    echo ""
    
    test_signal_processing || ((failed_tests++))
    echo ""
    
    test_communication || ((failed_tests++))
    echo ""
    
    test_utils || ((failed_tests++))
    echo ""
    
    test_integration || ((failed_tests++))
    echo ""
    
    # 总结
    if [ $failed_tests -eq 0 ]; then
        log_success "所有测试通过！系统功能正常"
        return 0
    else
        log_error "$failed_tests 个测试失败，请检查系统配置"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "脑机接口系统测试脚本"
    echo ""
    echo "用法: $0 [测试类型]"
    echo ""
    echo "测试类型:"
    echo "  all         运行所有测试（默认）"
    echo "  config      测试配置加载"
    echo "  data        测试数据采集"
    echo "  signal      测试信号处理"
    echo "  comm        测试通信模块"
    echo "  utils       测试工具模块"
    echo "  integ       测试集成功能"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0           # 运行所有测试"
    echo "  $0 config    # 只测试配置加载"
    echo ""
}

# 主逻辑
main() {
    case "${1:-all}" in
        "all")
            run_all_tests
            ;;
        "config")
            test_config_loading
            ;;
        "data")
            test_data_acquisition
            ;;
        "signal")
            test_signal_processing
            ;;
        "comm")
            test_communication
            ;;
        "utils")
            test_utils
            ;;
        "integ")
            test_integration
            ;;
        "help")
            show_help
            ;;
        *)
            log_error "未知测试类型: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行测试
main "$@"
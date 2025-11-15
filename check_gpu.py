import torch
import whisper

print("=" * 60)
print("GPU 检测")
print("=" * 60)

print(f"\nPyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"GPU设备数量: {torch.cuda.device_count()}")
    print(f"GPU名称: {torch.cuda.get_device_name(0)}")
    print(f"GPU显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    print("\n测试 Whisper GPU 加速...")
    model = whisper.load_model("tiny")
    print(f"模型设备: {next(model.parameters()).device}")
    
    if next(model.parameters()).device.type == "cuda":
        print("\n✓ GPU加速已启用！转录速度将提升10-20倍")
    else:
        print("\n✗ 模型在CPU上运行")
        print("可能原因:")
        print("1. PyTorch没有安装CUDA版本")
        print("2. 需要重新安装支持CUDA的PyTorch")
else:
    print("\n✗ CUDA不可用")
    print("需要安装支持CUDA的PyTorch版本")
    print("\n安装命令（CUDA 12.x）:")
    print("pip uninstall torch torchvision torchaudio")
    print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")

print("=" * 60)


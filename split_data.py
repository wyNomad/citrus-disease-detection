import os
import shutil
import random
from pathlib import Path
from tqdm import tqdm

# === ⚙️ 配置区 ===
# 1. 这里填你截图里的那个文件夹路径 (源数据)
#    注意：要指向包含 images 和 labels 的上一级目录
SOURCE_FOLDER = r"datasets/download_temp/testA"

# 2. 输出路径 (会自动创建)
OUTPUT_FOLDER = r"datasets/citrus_mini"

# 3. CPU 保护模式：只抽取多少张？(建议 100)
SAMPLE_NUM = 100


def main():
    source_path = Path(SOURCE_FOLDER)
    output_path = Path(OUTPUT_FOLDER)

    img_source_dir = source_path / "images"
    lbl_source_dir = source_path / "labels"

    if not img_source_dir.exists() or not lbl_source_dir.exists():
        print(f"❌ 错误: 在 {source_path} 下没找到 images 或 labels 文件夹！")
        print("请检查路径是否填对了 (比如是不是多了一层文件夹?)")
        return

    # 1. 整理所有图片
    # 支持常见图片格式
    all_imgs = list(img_source_dir.glob("*.jpg")) + list(img_source_dir.glob("*.png")) + list(
        img_source_dir.glob("*.jpeg"))

    if not all_imgs:
        print("❌ 没找到图片文件！")
        return

    print(f"🔍 原始数据共找到 {len(all_imgs)} 张图片")

    # 2. 随机抽样
    if len(all_imgs) > SAMPLE_NUM:
        selected_imgs = random.sample(all_imgs, SAMPLE_NUM)
        print(f"✂️ CPU模式开启: 随机抽取 {SAMPLE_NUM} 张进行微型训练...")
    else:
        selected_imgs = all_imgs

    # 3. 划分训练集和验证集 (8:2)
    random.shuffle(selected_imgs)
    split_idx = int(len(selected_imgs) * 0.8)
    train_imgs = selected_imgs[:split_idx]
    val_imgs = selected_imgs[split_idx:]

    # 创建目录结构
    dirs_to_create = [
        output_path / 'images/train', output_path / 'images/val',
        output_path / 'labels/train', output_path / 'labels/val'
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    print("🚀 开始搬运数据...")

    def copy_pairs(img_list, split_type):
        success_count = 0
        for img_path in tqdm(img_list, desc=f"Processing {split_type}"):
            # 寻找对应的标签文件 (假设文件名一致，只是后缀不同)
            # 例如: images/001.jpg -> labels/001.txt
            lbl_name = img_path.stem + ".txt"
            lbl_path = lbl_source_dir / lbl_name

            if not lbl_path.exists():
                # print(f"⚠️ 警告: 图片 {img_path.name} 没有对应的标签文件，跳过")
                continue

            # 复制图片
            target_img = output_path / 'images' / split_type / img_path.name
            shutil.copy(img_path, target_img)

            # 复制标签
            target_lbl = output_path / 'labels' / split_type / lbl_name
            shutil.copy(lbl_path, target_lbl)
            success_count += 1
        return success_count

    n_train = copy_pairs(train_imgs, "train")
    n_val = copy_pairs(val_imgs, "val")

    print(f"\n✅ 数据集准备完毕！")
    print(f"📂 保存位置: {OUTPUT_FOLDER}")
    print(f"📊 最终有效数据: 训练集 {n_train} 张, 验证集 {n_val} 张")
    print("👉 下一步：把 label_object.json 的内容发给我，我们写配置文件！")


if __name__ == "__main__":
    main()
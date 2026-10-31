import shutil
import random
from pathlib import Path
from tqdm import tqdm

# ==========================================
# 🎛️ 核心配置区 (以后主要改这里)
# ==========================================

# 1. [输入] 原始数据在哪里？
#    以后你要是用 testB，就把这里改成 .../testB 即可
#    注意：这个文件夹下面必须要有 images 和 labels 两个子文件夹
SOURCE_ROOT = r"datasets/download_temp/testA"

# 2. [输出] 准备好的数据存哪里？
#    指向你的训练专用目录 (custom_data.yaml 里配的那个路径)
TARGET_ROOT = r"datasets/citrus_mini"

# 3. [采样] 你的CPU只能吃多少张？
#    如果你想训练全量数据，把这里改成 None (注意首字母大写)
#    CPU用户建议保持 100-200，显卡用户可以设为 None
SAMPLE_NUM = 100

# 4. [清洗] 是否先清空目标文件夹？
#    True  = 每次运行前把 datasets/citrus_mini 删光重建 (推荐，最干净)
#    False = 保留原文件，把新图片追加进去 (仅用于混合不同来源的数据)
CLEAN_MODE = True

# 5. [比例] 训练集占比 (0.8 = 80% 训练, 20% 验证)
TRAIN_RATIO = 0.8


# ==========================================
# 🚀 核心逻辑区 (通常不需要修改)
# ==========================================

def main():
    source_path = Path(SOURCE_ROOT)
    target_path = Path(TARGET_ROOT)

    # --- 1. 检查源数据 ---
    if not source_path.exists():
        print(f"❌ 错误：找不到源数据目录: {source_path}")
        return

    # 收集所有可能的图片格式
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    all_imgs = []
    for ext in extensions:
        all_imgs.extend(list((source_path / "images").glob(ext)))
        # 有些数据集可能大小写不规范，尝试大写后缀
        all_imgs.extend(list((source_path / "images").glob(ext.upper())))

    total_imgs = len(all_imgs)
    if total_imgs == 0:
        print(f"❌ 错误：在 {source_path}/images 下没找到任何图片！")
        return

    print(f"🔍 扫描到源数据: {total_imgs} 张图片")

    # --- 2. 自动清洗旧数据 ---
    if CLEAN_MODE and target_path.exists():
        print(f"🧹 [清洗模式] 正在删除旧目录: {target_path} ...")
        shutil.rmtree(target_path)

    # 重建目录结构
    for split in ['train', 'val']:
        (target_path / 'images' / split).mkdir(parents=True, exist_ok=True)
        (target_path / 'labels' / split).mkdir(parents=True, exist_ok=True)

    # --- 3. 随机抽样 (CPU保护) ---
    if SAMPLE_NUM is not None and total_imgs > SAMPLE_NUM:
        print(f"✂️ [采样模式] 原图太多，随机抽取 {SAMPLE_NUM} 张用于轻量级训练...")
        selected_imgs = random.sample(all_imgs, SAMPLE_NUM)
    else:
        print("📦 [全量模式] 使用所有图片进行训练...")
        selected_imgs = all_imgs

    # --- 4. 打乱并切分 ---
    random.shuffle(selected_imgs)
    split_index = int(len(selected_imgs) * TRAIN_RATIO)

    train_imgs = selected_imgs[:split_index]
    val_imgs = selected_imgs[split_index:]

    # --- 5. 搬运工函数 ---
    def copy_files(img_list, split_name):
        count = 0
        desc = f"搬运 {split_name} 集"

        for img_path in tqdm(img_list, desc=desc):
            # 1. 构造标签路径
            # 假设 images/abc.jpg 对应 labels/abc.txt
            label_name = img_path.stem + ".txt"
            src_label = source_path / "labels" / label_name

            # 2. 检查标签是否存在 (没标签的图是垃圾数据，不能要)
            if not src_label.exists():
                # print(f"⚠️ 跳过无标签图片: {img_path.name}")
                continue

            # 3. 复制图片
            dst_img = target_path / 'images' / split_name / img_path.name
            shutil.copy(img_path, dst_img)

            # 4. 复制标签
            dst_label = target_path / 'labels' / split_name / label_name
            shutil.copy(src_label, dst_label)

            count += 1
        return count

    # --- 6. 执行搬运 ---
    print("🚀 开始划分数据集...")
    train_count = copy_files(train_imgs, 'train')
    val_count = copy_files(val_imgs, 'val')

    # --- 7. 总结报告 ---
    print("\n✅ 数据集制作完成！")
    print(f"📂 输出目录: {target_path}")
    print(f"📊 统计结果: 训练集 {train_count} 张 | 验证集 {val_count} 张")

    if SAMPLE_NUM is not None:
        print("💡 提示: 这是微型数据集。如果以后有了显卡，把配置里的 SAMPLE_NUM 改成 None 即可跑全量数据。")


if __name__ == "__main__":
    main()
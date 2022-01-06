# 残差网络 https://blog.csdn.net/a1105425455/article/details/117791839

# 1.加载必要的库
import os

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from constant import get_image_test, get_device

# 2.超参数
BATCH_SIZE = 32  # 每批处理的数据 一次性多少个
DEVICE = get_device()
EPOCHS = 4  # 训练数据集的轮次
# 3.图像处理
pipeline = transforms.Compose([transforms.ToTensor()])  # 将图片转换为Tensor


# 5.构建网络模型
class ResBlk(nn.Module):  # 定义Resnet Block模块
    """
    resnet block
    """

    def __init__(self, ch_in, ch_out, stride=1):  # 进入网络前先得知道传入层数和传出层数的设定
        """
        :param ch_in:
        :param ch_out:
        """
        super(ResBlk, self).__init__()  # 初始化

        # we add stride support for resbok, which is distinct from tutorials.
        # 根据resnet网络结构构建2个（block）块结构 第一层卷积 卷积核大小3*3,步长为1，边缘加1
        self.conv1 = nn.Conv2d(ch_in, ch_out, kernel_size=3, stride=stride, padding=1)
        # 将第一层卷积处理的信息通过BatchNorm2d
        self.bn1 = nn.BatchNorm2d(ch_out)
        # 第二块卷积接收第一块的输出，操作一样
        self.conv2 = nn.Conv2d(ch_out, ch_out, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(ch_out)

        # 确保输入维度等于输出维度
        self.extra = nn.Sequential()  # 先建一个空的extra
        if ch_out != ch_in:
            # [b, ch_in, h, w] => [b, ch_out, h, w]
            self.extra = nn.Sequential(
                nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=stride),
                nn.BatchNorm2d(ch_out)
            )

    def forward(self, x):  # 定义局部向前传播函数
        """
        :param x: [b, ch, h, w]
        :return:
        """
        out = F.relu(self.bn1(self.conv1(x)))  # 对第一块卷积后的数据再经过relu操作
        out = self.bn2(self.conv2(out))  # 第二块卷积后的数据输出
        # short cut.
        # extra module: [b, ch_in, h, w] => [b, ch_out, h, w]
        # element-wise add:
        out = self.extra(x) + out  # 将x传入extra经过2块（block）输出后与原始值进行相加
        out = F.relu(out)  # 调用relu，这里使用F.调用

        return out


class ResNet18(nn.Module):  # 构建resnet18层

    def __init__(self):
        super(ResNet18, self).__init__()

        self.conv1 = nn.Sequential(  # 首先定义一个卷积层
            nn.Conv2d(1, 32, kernel_size=3, stride=3, padding=0),
            nn.BatchNorm2d(32)
        )
        # followed 4 blocks 调用4次resnet网络结构，输出都是输入的2倍
        # [b, 64, h, w] => [b, 128, h ,w]
        self.blk1 = ResBlk(32, 64, stride=1)
        # [b, 128, h, w] => [b, 256, h, w]
        self.blk2 = ResBlk(64, 128, stride=1)
        # # [b, 256, h, w] => [b, 512, h, w]
        self.blk3 = ResBlk(128, 256, stride=1)
        # # [b, 512, h, w] => [b, 1024, h, w]
        self.blk4 = ResBlk(256, 256, stride=1)

        self.outlayer = nn.Linear(256 * 1 * 1, 10)  # 最后是全连接层

    def forward(self, x):  # 定义整个向前传播
        """
        :param x:
        :return:
        """
        x = F.relu(self.conv1(x))  # 先经过第一层卷积

        # [b, 64, h, w] => [b, 1024, h, w]
        x = self.blk1(x)  # 然后通过4次resnet网络结构
        x = self.blk2(x)
        x = self.blk3(x)
        x = self.blk4(x)

        # print('after conv:', x.shape) #[b, 512, 2, 2]
        # F.adaptive_avg_pool2d功能尾巴变为1,1，[b, 512, h, w] => [b, 512, 1, 1]
        x = F.adaptive_avg_pool2d(x, [1, 1])
        # print('after pool:', x.shape)
        x = x.view(x.size(0), -1)  # 平铺一维值
        x = self.outlayer(x)  # 全连接层

        return x


def load_model(path):
    model = ResNet18().to(DEVICE)  # 创建模型并将模型加载到指定设备上
    model.load_state_dict(torch.load(path))
    model.eval()  # 一定要使用model.eval()来固定dropout和归一化层，否则每次推理会生成不同的结果。
    if test(model):
        print("模型加载成功")
    else:
        print("模型加载失败")
    return model


def test(model):
    image_test, label_test = get_image_test(DEVICE, (1, 1, 28, 28))
    label_test = 7
    output = model(image_test)
    predicted = output.argmax(1)
    return predicted == label_test


def model_predict(img, model):
    if isinstance(model, ResNet18):
        imgFinal = torch.tensor(img, device=DEVICE, dtype=torch.float32).reshape(1, 1, 28, 28)
        output = model(imgFinal)
        pred = output.argmax(dim=1)
        return int(pred.data)
    return -1


def get_model_files():
    # 返回该模型对应的所有模型文件
    model_dir = os.path.split(__file__)[0]
    model_resNet = os.path.join(model_dir, "model_file", "model_resNet.ckpt")
    return [model_resNet]

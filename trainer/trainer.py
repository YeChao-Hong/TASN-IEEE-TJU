# import os
# import torch
# import torch.nn as nn
# from models import build_model, get_loss
#
# class Trainer(nn.Module):
#     def __init__(self, opt):
#         super(Trainer, self).__init__()
#         self.opt = opt
#         self.total_steps = 0
#         self.save_dir = os.path.join(opt.checkpoints_dir, opt.name)
#         self.device = (
#             torch.device("cuda:{}".format(opt.gpu_ids[0]))
#             if opt.gpu_ids and torch.cuda.is_available()
#             else torch.device("cpu")
#         )
#         self.opt = opt
#         self.model = build_model(opt.arch)
#
#         self.step_bias = (
#             0
#             if not opt.fine_tune
#             else int(opt.pretrained_model.split("_")[-1].split(".")[0]) + 1
#         )
#         if opt.fine_tune:
#             if os.path.exists(opt.pretrained_model):
#                 state_dict = torch.load(opt.pretrained_model, map_location="cpu")
#                 self.model.load_state_dict(state_dict["model"])
#                 self.total_steps = state_dict["total_steps"]
#                 print(f"Model loaded @ {opt.pretrained_model.split('/')[-1]}")
#             else:
#                 print(f"Pre-trained model file {opt.pretrained_model} not found. Starting training from scratch.")
#                 self.step_bias = 0
#
#         if opt.fix_encoder:
#             for name, p in self.model.named_parameters():
#                 if name.split(".")[0] in ["encoder"]:
#                     p.requires_grad = False
#
#         params = [p for p in self.model.parameters() if p.requires_grad]
#
#         if opt.optim == "adam":
#             self.optimizer = torch.optim.AdamW(
#                 params,
#                 lr=opt.lr,
#                 betas=(opt.beta1, 0.999),
#                 weight_decay=opt.weight_decay,
#             )
#         elif opt.optim == "sgd":
#             self.optimizer = torch.optim.SGD(
#                 params, lr=opt.lr, momentum=0.0, weight_decay=opt.weight_decay
#             )
#         else:
#             raise ValueError("optim should be [adam, sgd]")
#
#         self.criterion = get_loss().to(self.device)
#         self.criterion1 = nn.CrossEntropyLoss()
#
#         self.model = self.model.to(self.device)
#
#     def adjust_learning_rate(self, min_lr=1e-8):
#         for param_group in self.optimizer.param_groups:
#             if param_group["lr"] < min_lr:
#                 return False
#             param_group["lr"] /= 10.0
#         return True
#
#     def set_input(self, input):
#         self.input = input[0].to(self.device)
#         self.crops = [[t.to(self.device) for t in sublist] for sublist in input[1]]
#         self.label = input[2].to(self.device).float()
#
#     def forward(self):
#         self.get_features()
#         self.output, self.weights_max, self.weights_org = self.model.forward(
#             self.crops, self.features
#         )
#         self.output = self.output.view(-1)
#         self.loss = self.criterion(
#             self.weights_max, self.weights_org
#         ) + 10 * self.criterion1(self.output, self.label)
#
#     def get_loss(self):
#         loss = self.loss.data.tolist()
#         return loss[0] if isinstance(loss, type(list())) else loss
#
#     def optimize_parameters(self):
#         self.optimizer.zero_grad()
#         self.loss.backward()
#         self.optimizer.step()
#
#     def get_features(self):
#         self.features = self.model.get_features(self.input).to(
#             self.device
#         )  # shape: (batch_size
#
#     def eval(self):
#         self.model.eval()
#
#     def test(self):
#         with torch.no_grad():
#             self.forward()
#
#     def save_networks(self, save_filename):
#         save_path = os.path.join(self.save_dir, save_filename)
#
#         # serialize model and optimizer to dict
#         state_dict = {
#             "model": self.model.state_dict(),
#             "optimizer": self.optimizer.state_dict(),
#             "total_steps": self.total_steps,
#         }
#
#         torch.save(state_dict, save_path)

import os
import torch
import torch.nn as nn
from torch.optim import lr_scheduler

from models import build_model, get_loss


class Trainer(nn.Module):
    def __init__(self, opt):
        super().__init__()
        self.opt = opt
        self.total_steps = 0
        self.save_dir = os.path.join(opt.checkpoints_dir, opt.name)
        self.device = (
            torch.device("cuda:{}".format(opt.gpu_ids[0]))
            if opt.gpu_ids and torch.cuda.is_available()
            else torch.device("cpu")
        )
        self.model = build_model(opt.arch)

        self.step_bias = (
            0
            if not opt.fine_tune
            else int(opt.pretrained_model.split("_")[-1].split(".")[0]) + 1
        )
        if opt.fine_tune:
            state_dict = torch.load(opt.pretrained_model, map_location=self.device)
            self.model.load_state_dict(state_dict["model"])
            self.total_steps = state_dict["total_steps"]
            print(f"Model loaded @ {opt.pretrained_model.split('/')[-1]}")

        if opt.fix_encoder:
            trainable_params = []
            for name, p in self.model.named_parameters():
                if name.split(".")[0] in ["encoder"]:
                    p.requires_grad = False
                else:
                    p.requires_grad = True
                    trainable_params.append(p)
            params = trainable_params
        else:
            params = self.model.parameters()

        if opt.optim == "adam":
            self.optimizer = torch.optim.AdamW(
                params,
                lr=opt.lr,
                betas=(opt.beta1, 0.999),
                weight_decay=opt.weight_decay,
            )
        elif opt.optim == "sgd":
            self.optimizer = torch.optim.SGD(
                params, lr=opt.lr, momentum=0.0, weight_decay=opt.weight_decay
            )
        else:
            raise ValueError("optim should be [adam, sgd]")

        self.criterion = get_loss().to(self.device)
        self.criterion1 = nn.BCEWithLogitsLoss().to(self.device)
        self.model.to(self.device)

        self.scheduler = lr_scheduler.ReduceLROnPlateau(
        self.optimizer,
        # mode='min',
        mode='max',
        factor=0.1,
        patience=5,
        verbose=True
        )

    def set_input(self, input):
        self.input = input[0].to(self.device)
        self.crops = [[t.to(self.device) for t in sublist] for sublist in input[1]]
        # self.label = input[2].to(self.device)
        self.label = input[2].to(self.device).float()

    def forward(self):
        self.get_features()
        self.output, self.weights_max, self.weights_org = self.model.forward(
            self.crops, self.features
        )                                           #此处features是对输入LipFD.get_features的结果
        self.output = self.output.view(-1)
        self.loss =1 * self.criterion(
            self.weights_max, self.weights_org
        ) + 10 * self.criterion1(self.output, self.label)

    def get_loss(self):
        loss = self.loss.data.tolist()
        return loss[0] if isinstance(loss, type(list())) else loss

    def optimize_parameters(self):
        self.optimizer.zero_grad()
        self.loss.backward()
        self.optimizer.step()

    def get_features(self):
        self.features = self.model.get_features(self.input).to(
            self.device
        )  # shape: (batch_size

    def eval(self):
        self.model.eval()

    def test(self):
        with torch.no_grad():
            self.forward()

    def save_networks(self, save_filename):
        save_path = os.path.join(self.save_dir, save_filename)

        # serialize model and optimizer to dict
        state_dict = {
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "total_steps": self.total_steps,
        }

        torch.save(state_dict, save_path)

import argparse
import torch
import numpy as np
from data import AVLip
import torch.utils.data
from models import build_model
from sklearn.metrics import average_precision_score, confusion_matrix, accuracy_score
from tqdm import tqdm


def validate(model, loader, gpu_id):
    print("validating...")
    device = torch.device(f"cuda:{gpu_id[0]}" if torch.cuda.is_available() else "cpu")
    with torch.no_grad():
        y_true, y_pred = [], []
        for img, crops, label in tqdm(loader, desc="Validation Progress"):
            img_tens = img.to(device)
            crops_tens = [[t.to(device) for t in sublist] for sublist in crops]
            features = model.get_features(img_tens).to(device)

            y_pred.extend(model(crops_tens, features)[0].sigmoid().flatten().tolist())
            y_true.extend(label.flatten().tolist())

    y_true = np.array(y_true)
    y_pred = np.where(np.array(y_pred) >= 0.5, 1, 0)

    # Get AP
    ap = average_precision_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    tp, fn, fp, tn = cm.ravel()
    fnr = fn / (fn + tp)
    fpr = fp / (fp + tn)
    acc = accuracy_score(y_true, y_pred)

    return ap, fpr, fnr, acc


# def validate(model, loader, gpu_id):
#     print("validating...")
#     device = torch.device(f"cuda:{gpu_id[0]}" if torch.cuda.is_available() else "cpu")
#     with torch.no_grad():
#         y_true, y_pred = [], []
#         for img, crops, label in loader:
#             img_tens = img.to(device)
#             crops_tens = [[t.to(device) for t in sublist] for sublist in crops]
#             features = model.get_features(img_tens).to(device)
#
#             y_pred.extend(model(crops_tens, features)[0].sigmoid().flatten().tolist())
#             y_true.extend(label.flatten().tolist())
#     y_true = np.array(y_true)
#     y_pred = np.where(np.array(y_pred) >= 0.5, 1, 0)
#
#     # Get AP
#     ap = average_precision_score(y_true, y_pred)
#     cm = confusion_matrix(y_true, y_pred)
#     tp, fn, fp, tn = cm.ravel()
#     fnr = fn / (fn + tp)
#     fpr = fp / (fp + tn)
#     acc = accuracy_score(y_true, y_pred)
#     return ap, fpr, fnr, acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # parser.add_argument("--real_list_path", type=str, default="./datasets/val/0_real")
    # parser.add_argument("--fake_list_path", type=str, default="./datasets/val/1_fake")
    parser.add_argument("--real_list_path", type=str, default="/root/autodl-tmp/val_final/0_real")
    parser.add_argument("--fake_list_path", type=str, default="/root/autodl-tmp/val_final/1_fake")
    parser.add_argument("--max_sample", type=int, default=1000, help="max number of validate samples")
    parser.add_argument("--batch_size", type=int, default=5)
    parser.add_argument("--data_label", type=str, default="val")
    parser.add_argument("--arch", type=str, default="CLIP:ViT-L/14")
    # parser.add_argument("--ckpt", type=str, default="/tmp/pycharm_project_76/checkpoints/model_epoch_0.pth")
    parser.add_argument("--ckpt", type=str, default="/root/autodl-tmp/checkpoints/experiment_name/ff_lip_model_epoch_3.pth")
    parser.add_argument("--gpu", type=int, default=0)

    opt = parser.parse_args()

    device = torch.device(f"cuda:{opt.gpu}" if torch.cuda.is_available() else "cpu")
    print(f"Using cuda {opt.gpu} for inference.")

    model = build_model(opt.arch)
    state_dict = torch.load(opt.ckpt, map_location="cpu")
    model.load_state_dict(state_dict["model"])
    print("Model loaded.")
    model.eval()
    model.to(device)

    dataset = AVLip(opt)
    loader = data_loader = torch.utils.data.DataLoader(
        dataset, batch_size=opt.batch_size, shuffle=True
    )
    ap, fpr, fnr, acc = validate(model, loader, gpu_id=[opt.gpu])
    print(f"acc: {acc} ap: {ap} fpr: {fpr} fnr: {fnr}")

    #python validate.py --real_list_path. /datasets/val/0_real --fake_list_path./datasets/val/ 1_fake --ckpt./checkpoints/experiment_name/model_epoch_1.pth
 #acc: 0.5455079271873166 ap: 0.5237604866940078 fpr: 0.8393598103141672 fnr: 0.07678883071553229
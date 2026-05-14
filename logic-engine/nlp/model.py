import fasttext
import os
import random
#from sklearn.metrics import confusion_matrix, classification_report
#import pandas as pd
#import seaborn as sns
#import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "models", "fasttext.bin")
DATA_PATH = os.path.join(BASE_DIR, "nlp", "data", "commands.txt")
TEST_PATH = os.path.join(BASE_DIR, "nlp", "data", "test_data.txt")  # Nytt
#bayesian approach

def train():
    model = fasttext.train_supervised(
    #   input=DATA_PATH,
    #   epoch=200,
    #   lr=0.4,
    #   wordNgrams=3,    # catch more phrase patterns
    #   dim=50,          # more room to separate intents
    #   loss='softmax',
    #   minn=2,
    #   maxn=6,
    #   bucket=200000
        input=DATA_PATH,
        epoch=13,
        lr=1.2709756728344108,
        wordNgrams=3,
        dim=264,
        loss='softmax',
        bucket=200000
    )
    # check for overfitting
    n, p, r = model.test(DATA_PATH)
    print(f"Train precision: {p:.4f}")
    n, p, r = model.test(TEST_PATH)
    print(f"Test precision: {p:.4f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save_model(MODEL_PATH)
    return model

# def generate_confusion_matrix():
#     test_path = os.path.join(BASE_DIR, "nlp", "data", "test_data.txt")

#     y_true = []
#     y_pred = []

#     with open(test_path, 'r') as f:
#         for line in f:
#             line = line.strip()

#             # Skip empty lines
#             if not line:
#                 continue

#             parts = line.split(" ", 1)

#             # Skip malformed lines
#             if len(parts) < 2:
#                 print("Skipping malformed line:", line)
#                 continue

#             label = parts[0].replace("__label__", "")
#             text = parts[1]

#             pred_label, confidence = predict(text)

#             y_true.append(label)
#             y_pred.append(pred_label)

#     print("Samples collected:", len(y_true))

#     labels = sorted(list(set(y_true)))

#     cm = confusion_matrix(y_true, y_pred, labels=labels)

#     df_cm = pd.DataFrame(cm, index=labels, columns=labels)

#     plt.figure(figsize=(12, 10))

#     sns.heatmap(
#         df_cm,
#         annot=True,
#         fmt="d",
#         cmap="Blues"
#     )

#     plt.title("Confusion Matrix for fastText Intent Classifier")
#     plt.xlabel("Predicted Label")
#     plt.ylabel("True Label")

#     plt.tight_layout()

#     plt.savefig("confusion_matrix.png")

#     print("\nConfusion matrix image saved as confusion_matrix.png")

#     plt.show()
    
    
def cross_validate(k=5):
    all_lines = open(DATA_PATH).readlines()
    all_lines = [l.strip() for l in all_lines if l.strip()]
    random.seed(42)
    random.shuffle(all_lines)
    fold_size = len(all_lines) // k
    scores = []
    
    for i in range(k):
        test = all_lines[i*fold_size:(i+1)*fold_size]
        train = all_lines[:i*fold_size] + all_lines[(i+1)*fold_size:]
        
        with open("/tmp/cv_train.txt", "w") as f: f.writelines(train)
        with open("/tmp/cv_test.txt", "w") as f: f.writelines(test)
        
        m = fasttext.train_supervised(input="/tmp/cv_train.txt", epoch=50, lr=0.5, wordNgrams=4, dim=50)
        n, p, r = m.test("/tmp/cv_test.txt")
        scores.append(p)
        print(f"Fold {i+1}: precision={p:.4f}")
    
    print(f"Average: {sum(scores)/len(scores):.4f}")

def load_model():
    if not os.path.exists(MODEL_PATH):
        print("Training fastText model...")
        return train()
    return fasttext.load_model(MODEL_PATH)


model = load_model()


# def predict(text):
#     text = text.strip().replace("\n", " ")
#     labels, probs = model.predict(text)
#     intent = labels[0].replace("__label__", "")
#     return intent, probs[0]

# def predict(text):
#     text = text.strip().replace("\n", " ")
#     labels, probs = model.predict(text, k=3)

#     for l, p in zip(labels, probs):
#         print(l, p)

#     intent = labels[0].replace("__label__", "")
#     return intent, probs[0]

# def predict(text, threshold=0.55):
#     text = text.strip().replace("\n", " ")

#     labels, probs = model.predict(text)

#     intent = labels[0].replace("__label__", "")
#     confidence = probs[0]

#     if confidence < threshold:
#         return "unknown", confidence

#     return intent, confidence

def predict(text):
    text = text.lower().strip()
    
    # Hardcoded safety bypass
    if any(word in text for word in ["stop", "halt", "abort", "emergency"]):
        return "stop", 1.0  # Force a STOP with 100% confidence
        
    labels, probs = model.predict(text)
    intent = labels[0].replace("__label__", "")
    return intent, probs[0]

def evaluate():
    if not os.path.exists(MODEL_PATH):
        print("No model found, train first.")
        return

    test_path = os.path.join(BASE_DIR, "nlp", "data", "test_data.txt")
    if not os.path.exists(test_path):
        print("No test data found at", test_path)
        return

    print("\n─── Overall ───────────────────────────────")
    n, precision, recall = model.test(test_path)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    print(f"Examples : {n}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")

    print("\n─── Per intent class ──────────────────────")
    for label in model.labels:
        clean_label = label.replace("__label__", "")

        test_lines = []
        with open(test_path) as f:
            for line in f:
                if line.startswith(label + " "):
                    test_lines.append(line)

        if not test_lines:
            print(f"{clean_label:<30} No test examples found")
            continue

        tmp_path = "/tmp/fasttext_tmp.txt"
        with open(tmp_path, "w") as f:
            f.writelines(test_lines)

        n, p, r = model.test(tmp_path)
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        print(f"{clean_label:<30} N: {n}  P: {p:.4f}  R: {r:.4f}  F1: {f1:.4f}")


if __name__ == "__main__":
    evaluate()
    #generate_confusion_matrix()

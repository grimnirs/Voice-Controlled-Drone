import fasttext
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "models", "fasttext.bin")
DATA_PATH = os.path.join(BASE_DIR, "nlp", "data", "commands.txt")


def train():
    model = fasttext.train_supervised(
        input=DATA_PATH,
        epoch=200,
        lr=1.0,
        wordNgrams=3,
        minCount=1,
        loss='softmax'
    )

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save_model(MODEL_PATH)
    return model


def load_model():
    if not os.path.exists(MODEL_PATH):
        print("Training fastText model...")
        return train()
    return fasttext.load_model(MODEL_PATH)


model = load_model()


def predict(text):
    text = text.strip().replace("\n", " ")
    labels, probs = model.predict(text)
    intent = labels[0].replace("__label__", "")
    return intent, probs[0]
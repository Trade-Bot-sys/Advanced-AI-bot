import base64

# Decode model.b64
with open("ai_model/model.b64", "r") as f:
    model_base64 = f.read()
with open("ai_model/model.pkl", "wb") as f:
    f.write(base64.b64decode(model_base64))

# Decode scaler.b64
with open("ai_model/scaler.b64", "r") as f:
    scaler_base64 = f.read()
with open("ai_model/scaler.pkl", "wb") as f:
    f.write(base64.b64decode(scaler_base64))

print("✅ Decoding complete: model.pkl and scaler.pkl created.")

import replicate


model = replicate.models.get("laion-ai/erlich")

for uri in model.predict(prompt='dog', batch_size=8):
    print(uri)

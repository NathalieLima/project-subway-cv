# Modelos MediaPipe

Execute na raiz do projeto:

```bash
python download_models.py
```

Isso cria/baixa:

- `pose_landmarker_lite.task` — modos CORPO e PEITORAL;
- `face_landmarker.task` — modo ROSTO;
- `gesture_recognizer.task` — modo MAOS.

Os modelos sao carregados por bytes (`model_asset_buffer`) para reduzir problemas com caminhos Unicode no Windows.

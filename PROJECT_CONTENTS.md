# Subway Vision Controller v7 — conteúdo completo

## Estrutura

```text
subway_vision_controller_v7/
  .gitignore
  README.md
  calibration/__init__.py
  calibration/calibrator.py
  classifiers/__init__.py
  classifiers/body_classifier.py
  classifiers/face_classifier.py
  classifiers/hand_classifier.py
  classifiers/stabilizer.py
  classifiers/upper_body_classifier.py
  config.py
  controllers/__init__.py
  controllers/game_controller.py
  controllers/hand_gesture_manager.py
  controllers/hotkeys.py
  controllers/transition_manager.py
  download_models.py
  keyboard_test_receiver.py
  main.py
  models/README.md
  requirements.txt
  run.bat
  states.py
  tests/test_hands.py
  tests/test_logic.py
  vision/__init__.py
  vision/face_detector.py
  vision/hand_detector.py
  vision/hud.py
  vision/pose_detector.py
```

## `.gitignore`

```text
.venv/
__pycache__/
*.pyc
models/*.task
```

## `README.md`

```markdown
# Subway Vision Controller

Controle de jogos por visao computacional em tempo real. O projeto **nao implementa o jogo**: ele reconhece movimentos pela webcam e envia as setas do teclado ao Windows, permitindo controlar Subway Surfers no Google Play Games para PC ou outro jogo compatível.

## Arquitetura

```text
Pessoa -> Webcam -> OpenCV -> MediaPipe -> Classificador
       -> StateStabilizer -> TransitionManager -> GameController
       -> pynput -> teclado do Windows -> Google Play Games -> Subway Surfers
```

Modos:

- **CORPO**: corpo inteiro, usando ombros, quadris, joelhos e tornozelos.
- **PEITORAL**: enquadramento da cintura/umbigo ate acima da cabeca; somente ombros sao obrigatorios para o controle normal. Abrir os dois bracos envia F5 para reiniciar.
- **ROSTO**: apenas o rosto, usando yaw/pitch da cabeca.
- **MAOS**: gestos das duas maos usando `Open_Palm`, `Closed_Fist` e um coracao detectado pela geometria dos landmarks; o coracao envia F5.

## 1. Ambiente virtual

Recomendacao: Python 3.11 de 64 bits.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows CMD

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

O `requirements.txt` fixa MediaPipe 1.0.1 e limita as demais bibliotecas a faixas compativeis.

## 2. Baixar os modelos

Na raiz do projeto:

```bash
python download_models.py
```

O script baixa os modelos oficiais para:

```text
models/pose_landmarker_lite.task
models/face_landmarker.task
models/gesture_recognizer.task
```

Tambem e possivel baixa-los manualmente:

- Pose Landmarker Lite: `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task`
- Face Landmarker: `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`
- Gesture Recognizer: `https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task`

Os modelos sao carregados com `Path.read_bytes()` + `BaseOptions(model_asset_buffer=...)`. Isso evita depender do caminho nativo do arquivo e reduz problemas com diretorios Windows contendo caracteres Unicode.

## 3. Selecionar a camera

Edite `config.py`:

```python
CAMERA_INDEX = 0
```

Se uma webcam externa for a camera 1, por exemplo:

```python
CAMERA_INDEX = 1
```

A resolucao inicial e 1280x720 a 30 FPS.

## 4. Executar

```bash
python main.py
```

Ou, no Windows:

```text
run.bat
```

O terminal perguntara:

```text
Escolha o modo de controle:

1 - CORPO
2 - PEITORAL
3 - ROSTO
4 - MAOS
```

Depois da escolha, a calibracao inicial comeca automaticamente nos modos CORPO, PEITORAL e ROSTO. MAOS entra direto no controle. A interface abre em tela cheia, com camera, estado, FPS, comandos do modo e debug separados em um dashboard.

## 5. Atalhos globais

Os atalhos sao capturados pelo `pynput`, portanto funcionam mesmo quando o Google Play Games esta em primeiro plano:

- **F8**: iniciar/reiniciar calibracao.
- **F10**: encerrar a aplicacao.
- **ESC**: saida de emergencia quando a janela OpenCV esta em foco.

O envio de comandos e **automatico**: fica pausado somente durante a calibracao e e ativado assim que a baseline fica pronta. O usuario nao precisa ativar o controle manualmente.

## 6. Calibracao

A calibracao nunca usa um unico frame. Ela:

1. exibe uma contagem regressiva;
2. pede para ficar em posicao neutra;
3. coleta 30 frames validos;
4. calcula a **mediana** de cada caracteristica;
5. cria uma baseline individual.

F8 limpa o historico de estabilizacao, estado temporal do classificador, faixa interna do personagem e cooldowns. O envio e interrompido durante a calibracao e reativado automaticamente quando ela termina.

## 7. Modo CORPO

### Enquadramento

A pessoa deve aparecer de corpo inteiro, com ombros, quadris, joelhos e tornozelos visiveis.

### Lateral

```text
(current_torso_x - baseline_torso_x) / baseline_shoulder_width
```

Threshold inicial:

```python
LATERAL_THRESHOLD = 0.45
```

As linhas verticais desenhadas na tela sao calculadas diretamente da baseline e desse threshold.

### Pulo

Combina subida do quadril e dos tornozelos:

```text
jump_score = hip_lift * 0.70 + ankle_lift * 0.30
```

```python
JUMP_THRESHOLD = 0.18
```

### Agachamento

O modo CORPO usa duas formas de confirmar o agachamento: descida do quadril combinada com flexao dos joelhos, ou uma descida de quadril suficientemente profunda. Isso evita perder o gesto quando o angulo dos joelhos oscila no MediaPipe:

```python
CROUCH_HIP_THRESHOLD = 0.12
CROUCH_KNEE_ANGLE = 165.0
CROUCH_DEEP_HIP_THRESHOLD = 0.22
```

## 8. Modo PEITORAL

### Enquadramento

Recomendado: aproximadamente da cintura/umbigo ate acima da cabeca. Nao e necessario mostrar quadris, joelhos ou tornozelos. Os pontos obrigatorios sao apenas os dois ombros.

### Lateral

```python
UPPER_LATERAL_THRESHOLD = 0.45
```

### Pulo

O sistema mede a subida dos ombros e a velocidade vertical. Pulo pode ocorrer por:

- deslocamento vertical suficiente; ou
- deslocamento menor acompanhado de subida rapida.

```python
UPPER_JUMP_LIFT_THRESHOLD = 0.25
UPPER_JUMP_MIN_LIFT_WITH_VELOCITY = 0.10
UPPER_JUMP_UPWARD_VELOCITY = 0.85
```

### Agachamento

O agachamento e tratado como postura mantida:

```python
UPPER_CROUCH_DROP_THRESHOLD = 0.18
UPPER_CROUCH_MAX_UPWARD_VELOCITY = 0.45
UPPER_CROUCH_CONFIRM_SECONDS = 0.18
```

Ele e confirmado quando os ombros permanecem abaixo do limite pelo tempo configurado. A descida dos ombros e aceita normalmente; o candidato a agachamento so e cancelado quando existe uma **subida rapida**, o que torna o gesto bem mais facil de reconhecer sem exigir que a pessoa congele no ponto mais baixo. O pulo continua tendo prioridade.

O HUD mostra `SUBIDA`, `DESCIDA`, `VELOCIDADE` e `AGACHAMENTO` em tempo real para facilitar ajustes manuais.

### Reiniciar abrindo os bracos

No modo PEITORAL, abrir os dois bracos aproximadamente na horizontal gera `F5` uma unica vez. Pulsos sao usados apenas para esse gesto; se eles sairem da imagem, o controle normal por ombros continua funcionando.

```python
UPPER_RESTART_ARM_SPAN_THRESHOLD = 3.00
UPPER_RESTART_MIN_SIDE_EXTENSION = 0.60
UPPER_RESTART_MAX_VERTICAL_OFFSET = 0.95
```

- `ARM_SPAN`: distancia entre os dois pulsos dividida pela largura dos ombros;
- `MIN_SIDE_EXTENSION`: quanto cada pulso ultrapassa lateralmente a regiao dos ombros;
- `MAX_VERTICAL_OFFSET`: tolerancia para os bracos nao precisarem ficar perfeitamente retos.

O HUD mostra esses tres valores em tempo real. O estado `REINICIAR` precisa estabilizar e o `TransitionManager` envia apenas um F5 enquanto a pose for mantida. Para reiniciar novamente, abaixe/feche os bracos e abra-os de novo.

## 9. Modo ROSTO

Durante a calibracao, olhe naturalmente para frente.

O Face Landmarker fornece uma matriz de transformacao facial 3D. O programa extrai yaw e pitch, subtrai a baseline neutra, aplica os sinais configuraveis e suaviza os angulos por media exponencial.

```python
FACE_YAW_DIRECTION = -1.0
FACE_PITCH_DIRECTION = -1.0
FACE_YAW_THRESHOLD_DEG = 20.0
FACE_PITCH_THRESHOLD_DEG = 15.0
FACE_ANGLE_SMOOTHING_ALPHA = 0.25
```

Com a convencao padrao esperada:

- virar fisicamente para a esquerda -> ESQUERDA;
- virar fisicamente para a direita -> DIREITA;
- olhar para cima -> PULO;
- olhar para baixo -> AGACHADO.

Se sua camera/driver produzir sinais invertidos, troque `FACE_YAW_DIRECTION` ou `FACE_PITCH_DIRECTION` entre `-1.0` e `1.0`.

Movimentos pequenos permanecem dentro da zona neutra. O HUD mostra yaw/pitch suavizados e seus thresholds.


## 10. Modo MAOS

O modo MAOS usa o **MediaPipe Gesture Recognizer** com ate duas maos. Ele nao precisa de calibracao geometrica: ao selecionar a opcao 4, o envio de comandos fica ativo imediatamente.

Regras:

```text
mao esquerda aberta somente -> LEFT
mao direita aberta somente  -> RIGHT
duas maos abertas           -> UP / PULO
duas maos fechadas          -> DOWN / AGACHADO
coracao com as duas maos    -> F5 / REINICIAR
```

O gesto de coracao e personalizado. O MediaPipe fornece os 21 landmarks de cada mao e o projeto verifica se as pontas dos indicadores se aproximam na parte superior e as pontas dos polegares na parte inferior, mantendo uma abertura minima entre indicador e polegar de cada mao.

```python
HAND_HEART_CONTACT_RATIO = 0.75
HAND_HEART_MIN_OPENING_RATIO = 0.65
HAND_HEART_MIN_VERTICAL_GAP_RATIO = 0.35
```

As medidas sao normalizadas pelo tamanho medio das maos. O HUD mostra `Indicadores`, `Polegares` e `Gap vertical`, permitindo ajustar esses thresholds conforme distancia da camera e estilo do gesto.

Uma unica mao fechada nao gera comando. Gestos diferentes de `Open_Palm` e `Closed_Fist` tambem nao geram comando.

Cada gesto gera apenas **um** evento de teclado enquanto for mantido. Para repetir o mesmo comando, solte/baixe a mao, mude para um gesto neutro e execute o gesto novamente.

O HUD mostra o gesto reconhecido e o score para cada lado. O principal ajuste e:

```python
HAND_GESTURE_MIN_SCORE = 0.55
```

- diminua se `Open_Palm`/`Closed_Fist` aparecem com score baixo mesmo quando o gesto esta correto;
- aumente se ocorrerem falsos positivos.

Se esquerda e direita aparecerem trocadas no HUD:

```python
HAND_SWAP_SIDES = True
```

O modo usa uma janela de estabilizacao menor para responder rapidamente:

```python
HAND_SMOOTHING_WINDOW = 3
HAND_MIN_STATE_VOTES = 2
```

F8, nesse modo, apenas limpa o historico dos gestos e cooldowns; nao existe baseline para recalibrar.

## 11. Interface em tela cheia

Por padrao:

```python
FULLSCREEN = True
```

A interface usa a resolucao principal do Windows e organiza a tela em:

- camera grande a esquerda;
- modo, estado, FPS e status do controle no topo;
- comandos do modo na lateral direita;
- painel de debug/thresholds na lateral direita;
- atalhos no rodape.

Para voltar ao comportamento em janela durante desenvolvimento:

```python
FULLSCREEN = False
```

## 12. Logica das faixas

O estado visual representa a posicao fisica; as teclas representam deslocamentos do personagem entre faixas.

Exemplos:

```text
CENTRO -> ESQUERDA : LEFT
ESQUERDA -> CENTRO : RIGHT
CENTRO -> DIREITA  : RIGHT
DIREITA -> CENTRO  : LEFT
ESQUERDA -> DIREITA: RIGHT + RIGHT
DIREITA -> ESQUERDA: LEFT + LEFT
```

Permanecer na mesma faixa nao envia novas teclas.

PULO e AGACHADO nao modificam a faixa lateral armazenada. Cada entrada em PULO gera no maximo um `UP`; cada entrada em AGACHADO gera no maximo um `DOWN`.

## 13. SEM_POSE

Se corpo/rosto sumir da camera:

- a tela mostra `SEM_POSE`;
- nenhuma tecla e enviada;
- a baseline permanece;
- a faixa lateral permanece;
- o ultimo estado confiavel permanece no estabilizador.

`SEM_POSE` nao e inserido na janela de votacao.

## 14. Configurar Google Play Games

O Python nao acessa nenhuma API interna do Subway Surfers. Ele apenas gera eventos normais das setas do teclado.

No Google Play Games:

1. abra o Subway Surfers;
2. configure os controles para que as setas correspondam a esquerda, direita, pulo e agachamento;
3. deixe o jogo em primeiro plano;
4. ao concluir a calibracao, o controle ja estara ativo automaticamente.

Por padrao:

```python
REQUIRE_GAME_FOCUS = False
GAME_WINDOW_KEYWORDS = ("Subway Surfers", "Google Play Games")
```

Com `REQUIRE_GAME_FOCUS = False`, as setas sao enviadas independentemente do titulo da janela ativa, o que evita bloqueios por diferencas no titulo do Google Play Games. Isso tambem significa que as setas podem atingir outro programa se voce trocar de janela enquanto o controle estiver rodando.

Se depois voce quiser restringir o envio somente ao jogo, altere para `True` e ajuste `GAME_WINDOW_KEYWORDS` conforme o titulo real da janela.

## 15. Como testar antes de abrir o Subway Surfers

1. Em um primeiro terminal, execute `python keyboard_test_receiver.py`.
2. Em um segundo terminal, execute `python main.py` e calibre.
3. Assim que a calibracao terminar, o controle fica ativo automaticamente.
4. Mova-se. O primeiro terminal deve imprimir `LEFT`, `RIGHT`, `UP`, `DOWN` e `F5 / REINICIAR` quando voce fizer o gesto de reinicio.
5. Pressione ESC no receptor quando terminar.

Voce tambem pode usar um editor de texto ou qualquer interface que responda as setas.

Tambem rode os testes de logica:

```bash
python -m unittest discover -s tests -v
```

Eles validam transicoes entre faixas, bloqueio de repeticao, preservacao durante `SEM_POSE`, votacao, mediana de calibracao, coracao no modo MAOS, abertura dos bracos no PEITORAL e os cenarios de agachamento.

## 16. Ajuste de sensibilidade

### Se estiver sensivel demais

Aumente limites de deslocamento:

- `LATERAL_THRESHOLD`
- `UPPER_LATERAL_THRESHOLD`
- `JUMP_THRESHOLD`
- `UPPER_JUMP_LIFT_THRESHOLD`
- `UPPER_JUMP_UPWARD_VELOCITY`
- `UPPER_CROUCH_DROP_THRESHOLD`
- `FACE_YAW_THRESHOLD_DEG`
- `FACE_PITCH_THRESHOLD_DEG`

Para o rosto, diminuir `FACE_ANGLE_SMOOTHING_ALPHA` deixa a resposta mais suave/lenta.

Para agachamento PEITORAL, aumentar `UPPER_CROUCH_CONFIRM_SECONDS` ou `UPPER_CROUCH_DROP_THRESHOLD` reduz falsos positivos. Diminuir `UPPER_CROUCH_MAX_UPWARD_VELOCITY` faz uma pequena subida cancelar o agachamento mais cedo.

No CORPO, para exigir joelhos mais dobrados, **reduza** `CROUCH_KNEE_ANGLE`. Para exigir uma descida maior quando o angulo do joelho estiver ruim, aumente `CROUCH_DEEP_HIP_THRESHOLD`.

### Se estiver pouco sensivel

Faca o contrario: reduza os thresholds de deslocamento/angulo. Para o rosto, aumentar moderadamente `FACE_ANGLE_SMOOTHING_ALPHA` deixa a resposta mais rapida.

No CORPO, aumentar `CROUCH_KNEE_ANGLE` torna a condicao de joelho mais permissiva.

No PEITORAL, diminuir `UPPER_CROUCH_DROP_THRESHOLD` ou `UPPER_CROUCH_CONFIRM_SECONDS` confirma o agachamento mais facilmente. Aumentar `UPPER_CROUCH_MAX_UPWARD_VELOCITY` deixa a regra mais tolerante a pequenas oscilacoes para cima.

Altere um parametro de cada vez e use os valores do HUD como referencia.

### Ajustar o reinicio por gesto

**MAOS / coracao:** se o coracao estiver dificil, aumente `HAND_HEART_CONTACT_RATIO` aos poucos (por exemplo 0.85) e/ou reduza `HAND_HEART_MIN_VERTICAL_GAP_RATIO`. Se ocorrer falso positivo, faca o contrario.

**PEITORAL / bracos abertos:** se nao reconhecer, reduza `UPPER_RESTART_ARM_SPAN_THRESHOLD` e `UPPER_RESTART_MIN_SIDE_EXTENSION`, ou aumente `UPPER_RESTART_MAX_VERTICAL_OFFSET`. Use os valores `Span`, `Ext. lateral` e `Altura braco` do HUD.

## 17. Performance

O projeto usa:

- Pose Landmarker Lite;
- `num_poses=1`;
- `RunningMode.VIDEO`;
- timestamp monotonicamente crescente;
- somente o detector necessario ao modo escolhido;
- uma unica webcam e processamento sequencial de baixa latencia.

O FPS real depende de CPU, webcam, iluminacao e resolucao. Se necessario, reduza `CAMERA_WIDTH`/`CAMERA_HEIGHT` mantendo os mesmos classificadores.

## 18. Troubleshooting

### Modelo nao encontrado

Execute:

```bash
python download_models.py
```

Confira os nomes exatos em `models/`.

### Camera nao abre

Troque `CAMERA_INDEX` entre 0, 1, 2... e feche outros programas que estejam usando a webcam.

### Nenhuma tecla chega ao jogo

- confirme que a calibracao terminou e o HUD mostra `CONTROLE DO JOGO: ATIVO`;
- confira o mapeamento das setas no Google Play Games;
- execute `keyboard_test_receiver.py` para confirmar que o Python realmente esta gerando as setas;
- no Windows, se o jogo estiver sendo executado como Administrador, execute o terminal/Python com o mesmo nivel de permissao.

### Direcoes do rosto invertidas

Troque o sinal de `FACE_YAW_DIRECTION` e/ou `FACE_PITCH_DIRECTION`.

### Rosto muda de estado com pequenos movimentos

Aumente `FACE_YAW_THRESHOLD_DEG` e `FACE_PITCH_THRESHOLD_DEG`; se necessario, reduza `FACE_ANGLE_SMOOTHING_ALPHA`.

### PEITORAL confunde preparacao de pulo com agachamento

Aumente `UPPER_CROUCH_CONFIRM_SECONDS` ou `UPPER_CROUCH_DROP_THRESHOLD`, ou reduza `UPPER_CROUCH_MAX_UPWARD_VELOCITY`. Observe `DESCIDA`, `VELOCIDADE` e `AGACHAMENTO` no HUD.

### Coracao nao envia F5

Confirme no painel de debug se `Coracao` muda para `DETECTADO`. Se nao mudar, aproxime as pontas dos dois indicadores e dos dois polegares e observe as tres metricas do painel. Se o estado chegar a `REINICIAR`, o terminal deve registrar `[TECLADO] F5 enviado`.

### Bracos abertos nao enviam F5 no PEITORAL

Mantenha os dois pulsos visiveis e abra os bracos aproximadamente na altura dos ombros. Observe `Span`, `Ext. lateral` e `Altura braco`. O controle normal do PEITORAL continua funcionando mesmo quando os pulsos nao estao detectados.

### Baixo FPS

Reduza para 960x540 ou 640x480 em `config.py`, melhore a iluminacao e feche aplicativos pesados.
```

## `calibration/__init__.py`

```python

```

## `calibration/calibrator.py`

```python
"""Maquina de estados simples para calibracao por mediana."""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field

from config import CALIBRATION_COUNTDOWN_SECONDS, CALIBRATION_SAMPLES


@dataclass
class Calibrator:
    countdown_seconds: float = CALIBRATION_COUNTDOWN_SECONDS
    sample_count: int = CALIBRATION_SAMPLES
    active: bool = False
    complete: bool = False
    started_at: float = 0.0
    samples: list[dict[str, float]] = field(default_factory=list)
    baseline: dict[str, float] | None = None

    def start(self) -> None:
        self.active = True
        self.complete = False
        self.started_at = time.perf_counter()
        self.samples.clear()
        self.baseline = None

    def reset(self) -> None:
        self.active = False
        self.complete = False
        self.samples.clear()
        self.baseline = None

    def update(self, features: dict[str, float] | None) -> dict[str, float] | None:
        if not self.active:
            return None

        elapsed = time.perf_counter() - self.started_at
        if elapsed < self.countdown_seconds:
            return None

        if features is not None:
            self.samples.append(dict(features))

        if len(self.samples) < self.sample_count:
            return None

        common_keys = set.intersection(*(set(s.keys()) for s in self.samples))
        baseline = {
            key: float(statistics.median(sample[key] for sample in self.samples))
            for key in sorted(common_keys)
        }
        self.baseline = baseline
        self.active = False
        self.complete = True
        return baseline

    def message(self) -> str:
        if self.complete:
            return "CALIBRACAO CONCLUIDA"
        if not self.active:
            return "PRESSIONE F8 PARA CALIBRAR"

        elapsed = time.perf_counter() - self.started_at
        remaining = self.countdown_seconds - elapsed
        if remaining > 0:
            return f"FIQUE PARADO... {max(1, int(remaining + 0.999))}"
        return f"CALIBRANDO - NAO SE MOVA ({len(self.samples)}/{self.sample_count})"
```

## `classifiers/__init__.py`

```python

```

## `classifiers/body_classifier.py`

```python
"""Classificador do modo CORPO."""
from __future__ import annotations

import math
from typing import Any

from config import (
    CROUCH_DEEP_HIP_THRESHOLD,
    CROUCH_HIP_THRESHOLD,
    CROUCH_KNEE_ANGLE,
    JUMP_THRESHOLD,
    LATERAL_THRESHOLD,
    POSE_MIN_VISIBILITY,
)
from states import Estado


class BodyClassifier:
    # Indices do MediaPipe Pose.
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}

    @staticmethod
    def _ok(lm: Any) -> bool:
        visibility = getattr(lm, "visibility", 1.0)
        presence = getattr(lm, "presence", 1.0)
        return visibility >= POSE_MIN_VISIBILITY and presence >= 0.3

    @staticmethod
    def _mid(a: Any, b: Any) -> tuple[float, float]:
        return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _angle(a: Any, b: Any, c: Any) -> float:
        ba = (a.x - b.x, a.y - b.y)
        bc = (c.x - b.x, c.y - b.y)
        denom = math.hypot(*ba) * math.hypot(*bc)
        if denom <= 1e-8:
            return 180.0
        cos_angle = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1]) / denom))
        return math.degrees(math.acos(cos_angle))

    def extrair_features(self, landmarks: list[Any] | None) -> dict[str, float] | None:
        if not landmarks or len(landmarks) <= self.RIGHT_ANKLE:
            return None

        idxs = [
            self.LEFT_SHOULDER,
            self.RIGHT_SHOULDER,
            self.LEFT_HIP,
            self.RIGHT_HIP,
            self.LEFT_KNEE,
            self.RIGHT_KNEE,
            self.LEFT_ANKLE,
            self.RIGHT_ANKLE,
        ]
        if not all(self._ok(landmarks[i]) for i in idxs):
            return None

        ls, rs = landmarks[self.LEFT_SHOULDER], landmarks[self.RIGHT_SHOULDER]
        lh, rh = landmarks[self.LEFT_HIP], landmarks[self.RIGHT_HIP]
        lk, rk = landmarks[self.LEFT_KNEE], landmarks[self.RIGHT_KNEE]
        la, ra = landmarks[self.LEFT_ANKLE], landmarks[self.RIGHT_ANKLE]

        shoulder = self._mid(ls, rs)
        hip = self._mid(lh, rh)
        ankle = self._mid(la, ra)
        torso = ((shoulder[0] + hip[0]) / 2.0, (shoulder[1] + hip[1]) / 2.0)

        shoulder_width = self._distance((ls.x, ls.y), (rs.x, rs.y))
        torso_height = self._distance(shoulder, hip)
        if shoulder_width <= 1e-5 or torso_height <= 1e-5:
            return None

        return {
            "torso_x": torso[0],
            "hip_x": hip[0],
            "hip_y": hip[1],
            "ankle_y": ankle[1],
            "shoulder_width": shoulder_width,
            "torso_height": torso_height,
            "left_knee_angle": self._angle(lh, lk, la),
            "right_knee_angle": self._angle(rh, rk, ra),
        }

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        self.baseline = dict(baseline)
        self.debug = {}

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        del timestamp_s
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        b = self.baseline
        width = max(b["shoulder_width"], 1e-5)
        torso_h = max(b["torso_height"], 1e-5)

        lateral = (features["torso_x"] - b["torso_x"]) / width
        hip_lift = (b["hip_y"] - features["hip_y"]) / torso_h
        ankle_lift = (b["ankle_y"] - features["ankle_y"]) / torso_h
        jump_score = hip_lift * 0.70 + ankle_lift * 0.30
        hip_drop = (features["hip_y"] - b["hip_y"]) / torso_h
        knee_angle = (features["left_knee_angle"] + features["right_knee_angle"]) / 2.0

        crouch_by_posture = (
            hip_drop >= CROUCH_HIP_THRESHOLD
            and knee_angle <= CROUCH_KNEE_ANGLE
        )
        # Se o quadril desceu muito, aceitamos o agachamento mesmo que o angulo
        # estimado dos joelhos esteja ruidoso ou parcialmente ocluido.
        crouch_by_depth = hip_drop >= CROUCH_DEEP_HIP_THRESHOLD

        self.debug = {
            "lateral": lateral,
            "jump_score": jump_score,
            "hip_drop": hip_drop,
            "knee_angle": knee_angle,
            "crouch_by_posture": 1.0 if crouch_by_posture else 0.0,
            "crouch_by_depth": 1.0 if crouch_by_depth else 0.0,
        }

        # Movimento vertical tem prioridade, mas nao altera a faixa interna do jogo.
        if jump_score >= JUMP_THRESHOLD:
            return Estado.PULO
        if crouch_by_posture or crouch_by_depth:
            return Estado.AGACHADO

        if lateral <= -LATERAL_THRESHOLD:
            return Estado.ESQUERDA
        if lateral >= LATERAL_THRESHOLD:
            return Estado.DIREITA
        return Estado.CENTRO

    def limites_guias(self) -> dict[str, float] | None:
        if self.baseline is None:
            return None
        return {
            "left_x": self.baseline["torso_x"] - self.baseline["shoulder_width"] * LATERAL_THRESHOLD,
            "right_x": self.baseline["torso_x"] + self.baseline["shoulder_width"] * LATERAL_THRESHOLD,
        }
```

## `classifiers/face_classifier.py`

```python
"""Classificador do modo ROSTO usando yaw e pitch da matriz facial 3D."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from config import (
    FACE_ANGLE_SMOOTHING_ALPHA,
    FACE_PITCH_DIRECTION,
    FACE_PITCH_THRESHOLD_DEG,
    FACE_YAW_DIRECTION,
    FACE_YAW_THRESHOLD_DEG,
)
from states import Estado


class FaceClassifier:
    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}
        self._smooth_yaw: float | None = None
        self._smooth_pitch: float | None = None

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}
        self._smooth_yaw = None
        self._smooth_pitch = None

    def reset_temporal(self) -> None:
        self._smooth_yaw = None
        self._smooth_pitch = None
        self.debug = {}

    @staticmethod
    def _rotation_to_angles(matrix: np.ndarray) -> tuple[float, float]:
        """Converte a rotacao da matriz facial em yaw(Y) e pitch(X), em graus.

        A convencao de sinal pode variar com camera/espelhamento, por isso o
        resultado ainda passa por FACE_YAW_DIRECTION/FACE_PITCH_DIRECTION.
        """
        r = np.asarray(matrix, dtype=float)
        if r.shape[0] < 3 or r.shape[1] < 3:
            raise ValueError("Matriz facial invalida")
        r = r[:3, :3]

        pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
        yaw = math.degrees(math.atan2(-r[2, 0], math.hypot(r[2, 1], r[2, 2])))
        return yaw, pitch

    def extrair_features(self, face_data: dict[str, Any] | None) -> dict[str, float] | None:
        if not face_data:
            return None
        matrix = face_data.get("matrix")
        if matrix is None:
            return None
        try:
            yaw, pitch = self._rotation_to_angles(np.asarray(matrix))
        except (ValueError, TypeError, IndexError):
            return None
        return {"yaw": yaw, "pitch": pitch}

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        self.baseline = dict(baseline)
        self.reset_temporal()

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        del timestamp_s
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        raw_yaw = (features["yaw"] - self.baseline["yaw"]) * FACE_YAW_DIRECTION
        raw_pitch = (features["pitch"] - self.baseline["pitch"]) * FACE_PITCH_DIRECTION

        alpha = FACE_ANGLE_SMOOTHING_ALPHA
        if self._smooth_yaw is None:
            self._smooth_yaw = raw_yaw
            self._smooth_pitch = raw_pitch
        else:
            self._smooth_yaw = alpha * raw_yaw + (1.0 - alpha) * self._smooth_yaw
            self._smooth_pitch = alpha * raw_pitch + (1.0 - alpha) * self._smooth_pitch

        yaw = float(self._smooth_yaw)
        pitch = float(self._smooth_pitch)
        self.debug = {
            "raw_yaw": raw_yaw,
            "raw_pitch": raw_pitch,
            "yaw": yaw,
            "pitch": pitch,
        }

        # Vertical primeiro para que olhar para cima/baixo seja inequívoco.
        if pitch >= FACE_PITCH_THRESHOLD_DEG:
            return Estado.PULO
        if pitch <= -FACE_PITCH_THRESHOLD_DEG:
            return Estado.AGACHADO
        if yaw <= -FACE_YAW_THRESHOLD_DEG:
            return Estado.ESQUERDA
        if yaw >= FACE_YAW_THRESHOLD_DEG:
            return Estado.DIREITA
        return Estado.CENTRO
```

## `classifiers/hand_classifier.py`

```python
"""Classificacao do modo MAOS a partir dos gestos e landmarks do MediaPipe."""
from __future__ import annotations

import math
from typing import Any

from config import (
    HAND_GESTURE_MIN_SCORE,
    HAND_HEART_CONTACT_RATIO,
    HAND_HEART_MIN_OPENING_RATIO,
    HAND_HEART_MIN_VERTICAL_GAP_RATIO,
)
from states import Estado


class HandClassifier:
    """Converte combinacoes de gestos em estados do jogo.

    Regras:
    - esquerda aberta somente -> ESQUERDA
    - direita aberta somente -> DIREITA
    - duas abertas -> PULO
    - duas fechadas -> AGACHADO
    - coracao com duas maos -> REINICIAR (F5)
    """

    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    PINKY_MCP = 17

    def __init__(self) -> None:
        self.debug: dict[str, Any] = {}

    def reset(self) -> None:
        self.debug = {}

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        _ = baseline

    @staticmethod
    def _distance(a: Any, b: Any) -> float:
        return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))

    def _hand_scale(self, hand: dict[str, Any]) -> float:
        landmarks = hand.get("landmarks") or []
        if len(landmarks) <= self.PINKY_MCP:
            return 0.0
        wrist_to_middle = self._distance(landmarks[self.WRIST], landmarks[self.MIDDLE_MCP])
        palm_width = self._distance(landmarks[self.INDEX_MCP], landmarks[self.PINKY_MCP])
        return max(wrist_to_middle, palm_width, 1e-5)

    def _detect_heart(
        self,
        left: dict[str, Any] | None,
        right: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, float]]:
        """Detecta um coracao feito com as duas maos.

        O gesto esperado e o coracao classico de duas maos: indicadores se
        encontram na parte superior e polegares na parte inferior.
        """
        empty = {
            "heart_index_contact": 99.0,
            "heart_thumb_contact": 99.0,
            "heart_left_opening": 0.0,
            "heart_right_opening": 0.0,
            "heart_vertical_gap": 0.0,
        }
        if not left or not right:
            return False, empty

        ll = left.get("landmarks") or []
        rl = right.get("landmarks") or []
        if len(ll) <= self.PINKY_MCP or len(rl) <= self.PINKY_MCP:
            return False, empty

        scale = (self._hand_scale(left) + self._hand_scale(right)) / 2.0
        if scale <= 1e-5:
            return False, empty

        index_contact = self._distance(ll[self.INDEX_TIP], rl[self.INDEX_TIP]) / scale
        thumb_contact = self._distance(ll[self.THUMB_TIP], rl[self.THUMB_TIP]) / scale
        left_opening = self._distance(ll[self.INDEX_TIP], ll[self.THUMB_TIP]) / scale
        right_opening = self._distance(rl[self.INDEX_TIP], rl[self.THUMB_TIP]) / scale

        index_center_y = (float(ll[self.INDEX_TIP].y) + float(rl[self.INDEX_TIP].y)) / 2.0
        thumb_center_y = (float(ll[self.THUMB_TIP].y) + float(rl[self.THUMB_TIP].y)) / 2.0
        vertical_gap = (thumb_center_y - index_center_y) / scale

        metrics = {
            "heart_index_contact": index_contact,
            "heart_thumb_contact": thumb_contact,
            "heart_left_opening": left_opening,
            "heart_right_opening": right_opening,
            "heart_vertical_gap": vertical_gap,
        }

        detected = (
            index_contact <= HAND_HEART_CONTACT_RATIO
            and thumb_contact <= HAND_HEART_CONTACT_RATIO
            and left_opening >= HAND_HEART_MIN_OPENING_RATIO
            and right_opening >= HAND_HEART_MIN_OPENING_RATIO
            and vertical_gap >= HAND_HEART_MIN_VERTICAL_GAP_RATIO
        )
        return detected, metrics

    @staticmethod
    def _valid_gesture(hand: dict[str, Any] | None) -> tuple[str, float]:
        if not hand:
            return "AUSENTE", 0.0
        gesture = str(hand.get("gesture", "None"))
        score = float(hand.get("gesture_score", 0.0))
        if score < HAND_GESTURE_MIN_SCORE:
            return "INCERTO", score
        if gesture == "Open_Palm":
            return "ABERTA", score
        if gesture == "Closed_Fist":
            return "FECHADA", score
        return "OUTRO", score

    def classificar(self, hand_data: dict[str, Any] | None, now: float | None = None) -> Estado:
        _ = now
        hands = (hand_data or {}).get("hands", [])

        left: dict[str, Any] | None = None
        right: dict[str, Any] | None = None
        for hand in hands:
            side = str(hand.get("side", "UNKNOWN")).upper()
            if side == "LEFT":
                left = hand
            elif side == "RIGHT":
                right = hand

        left_gesture, left_score = self._valid_gesture(left)
        right_gesture, right_score = self._valid_gesture(right)
        heart_detected, heart_metrics = self._detect_heart(left, right)

        self.debug = {
            "left_gesture": left_gesture,
            "left_score": left_score,
            "right_gesture": right_gesture,
            "right_score": right_score,
            "hands_detected": len(hands),
            "heart_detected": 1.0 if heart_detected else 0.0,
            **heart_metrics,
        }

        if not hands:
            return Estado.SEM_POSE

        # Reinicio tem prioridade sobre os outros gestos.
        if heart_detected:
            return Estado.REINICIAR

        if left_gesture == "ABERTA" and right_gesture == "ABERTA":
            return Estado.PULO
        if left_gesture == "FECHADA" and right_gesture == "FECHADA":
            return Estado.AGACHADO

        if left_gesture == "ABERTA" and right_gesture != "ABERTA":
            return Estado.ESQUERDA
        if right_gesture == "ABERTA" and left_gesture != "ABERTA":
            return Estado.DIREITA

        return Estado.CENTRO
```

## `classifiers/stabilizer.py`

```python
from collections import Counter, deque
from typing import Deque

from config import MIN_STATE_VOTES, SMOOTHING_WINDOW
from states import Estado


class StateStabilizer:
    """Suaviza os estados por votacao em uma janela curta.

    SEM_POSE e propositalmente ignorado no historico para que a perda de
    deteccao nao apague o ultimo estado fisico confiavel.

    PULO recebe um tratamento especial: como e um movimento muito rapido,
    esperar MIN_STATE_VOTES (3 por padrao) em toda a janela pode fazer o evento
    desaparecer antes de chegar ao controlador. Para continuar evitando falsos
    positivos de um unico frame, o pulo e confirmado quando aparece em dois dos
    tres frames mais recentes.
    """

    def __init__(self, window_size: int = SMOOTHING_WINDOW, min_votes: int = MIN_STATE_VOTES):
        self.window_size = window_size
        self.min_votes = min_votes
        self._history: Deque[Estado] = deque(maxlen=window_size)
        self._stable_state = Estado.CENTRO

    @property
    def stable_state(self) -> Estado:
        return self._stable_state

    def reset(self, initial_state: Estado = Estado.CENTRO) -> None:
        self._history.clear()
        self._stable_state = initial_state

    def update(self, state: Estado) -> Estado:
        if state == Estado.SEM_POSE:
            return Estado.SEM_POSE

        self._history.append(state)

        # PULO e um evento curto. Exigir 3 votos em 5 frames pode engolir o
        # movimento antes de ele chegar ao TransitionManager. Dois votos nos
        # tres frames mais recentes continuam filtrando um falso positivo de
        # apenas um frame, mas deixam o comando UP responder a tempo.
        recent = list(self._history)[-3:]
        jump_votes = sum(1 for item in recent if item == Estado.PULO)
        if jump_votes >= 2:
            self._stable_state = Estado.PULO
            return self._stable_state

        counts = Counter(self._history)
        candidate, votes = counts.most_common(1)[0]

        if votes >= self.min_votes:
            self._stable_state = candidate

        return self._stable_state
```

## `classifiers/upper_body_classifier.py`

```python
"""Classificador do modo PEITORAL.

Os ombros continuam sendo os unicos pontos obrigatorios para o controle normal.
Pulsos sao opcionais e usados apenas para o gesto de reinicio com bracos abertos.
"""
from __future__ import annotations

import math
from typing import Any

from config import (
    POSE_MIN_VISIBILITY,
    UPPER_CROUCH_CONFIRM_SECONDS,
    UPPER_CROUCH_DROP_THRESHOLD,
    UPPER_CROUCH_MAX_UPWARD_VELOCITY,
    UPPER_JUMP_LIFT_THRESHOLD,
    UPPER_JUMP_MIN_LIFT_WITH_VELOCITY,
    UPPER_JUMP_UPWARD_VELOCITY,
    UPPER_LATERAL_THRESHOLD,
    UPPER_RESTART_ARM_SPAN_THRESHOLD,
    UPPER_RESTART_MAX_VERTICAL_OFFSET,
    UPPER_RESTART_MIN_SIDE_EXTENSION,
)
from states import Estado


class UpperBodyClassifier:
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16

    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}
        self._prev_y: float | None = None
        self._prev_t: float | None = None
        self._crouch_since: float | None = None

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}
        self._prev_y = None
        self._prev_t = None
        self._crouch_since = None

    def reset_temporal(self) -> None:
        self._prev_y = None
        self._prev_t = None
        self._crouch_since = None
        self.debug = {}

    @staticmethod
    def _ok(lm: Any) -> bool:
        visibility = getattr(lm, "visibility", 1.0)
        presence = getattr(lm, "presence", 1.0)
        return visibility >= POSE_MIN_VISIBILITY and presence >= 0.3

    def extrair_features(self, landmarks: list[Any] | None) -> dict[str, float] | None:
        if not landmarks or len(landmarks) <= self.RIGHT_SHOULDER:
            return None
        ls = landmarks[self.LEFT_SHOULDER]
        rs = landmarks[self.RIGHT_SHOULDER]
        if not self._ok(ls) or not self._ok(rs):
            return None

        shoulder_x = (ls.x + rs.x) / 2.0
        shoulder_y = (ls.y + rs.y) / 2.0
        shoulder_width = math.hypot(ls.x - rs.x, ls.y - rs.y)
        if shoulder_width <= 1e-5:
            return None

        features: dict[str, float] = {
            "shoulder_x": shoulder_x,
            "shoulder_y": shoulder_y,
            "shoulder_width": shoulder_width,
        }

        # Pulsos sao opcionais. A ausencia deles nao invalida PEITORAL.
        if len(landmarks) > self.RIGHT_WRIST:
            lw = landmarks[self.LEFT_WRIST]
            rw = landmarks[self.RIGHT_WRIST]
            if self._ok(lw) and self._ok(rw):
                wrist_span = abs(float(lw.x) - float(rw.x)) / shoulder_width
                shoulder_min_x = min(float(ls.x), float(rs.x))
                shoulder_max_x = max(float(ls.x), float(rs.x))
                wrist_min_x = min(float(lw.x), float(rw.x))
                wrist_max_x = max(float(lw.x), float(rw.x))
                left_extension = (shoulder_min_x - wrist_min_x) / shoulder_width
                right_extension = (wrist_max_x - shoulder_max_x) / shoulder_width
                min_side_extension = min(left_extension, right_extension)
                vertical_offset = (
                    abs(float(lw.y) - shoulder_y) + abs(float(rw.y) - shoulder_y)
                ) / (2.0 * shoulder_width)

                features.update({
                    "arm_span": wrist_span,
                    "arm_min_side_extension": min_side_extension,
                    "arm_vertical_offset": vertical_offset,
                })

        return features

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        # A baseline pode conter metricas opcionais de bracos coletadas durante
        # a calibracao; elas nao sao necessarias para o classificador.
        self.baseline = {
            "shoulder_x": baseline["shoulder_x"],
            "shoulder_y": baseline["shoulder_y"],
            "shoulder_width": baseline["shoulder_width"],
        }
        self.reset_temporal()

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        b = self.baseline
        width = max(b["shoulder_width"], 1e-5)
        y = features["shoulder_y"]

        lateral = (features["shoulder_x"] - b["shoulder_x"]) / width
        lift = (b["shoulder_y"] - y) / width
        drop = (y - b["shoulder_y"]) / width

        velocity = 0.0
        if self._prev_y is not None and self._prev_t is not None:
            dt = max(timestamp_s - self._prev_t, 1e-4)
            velocity = (self._prev_y - y) / width / dt
        self._prev_y = y
        self._prev_t = timestamp_s

        arm_span = float(features.get("arm_span", 0.0))
        arm_min_side_extension = float(features.get("arm_min_side_extension", -99.0))
        arm_vertical_offset = float(features.get("arm_vertical_offset", 99.0))
        arms_open = (
            arm_span >= UPPER_RESTART_ARM_SPAN_THRESHOLD
            and arm_min_side_extension >= UPPER_RESTART_MIN_SIDE_EXTENSION
            and arm_vertical_offset <= UPPER_RESTART_MAX_VERTICAL_OFFSET
        )

        # Abrir os dois bracos e o gesto de reinicio e tem prioridade.
        if arms_open:
            self._crouch_since = None
            crouch_time = 0.0
            state = Estado.REINICIAR
            jump_by_height = False
            jump_by_speed = False
        else:
            jump_by_height = lift >= UPPER_JUMP_LIFT_THRESHOLD
            jump_by_speed = (
                lift >= UPPER_JUMP_MIN_LIFT_WITH_VELOCITY
                and velocity >= UPPER_JUMP_UPWARD_VELOCITY
            )
            if jump_by_height or jump_by_speed:
                self._crouch_since = None
                crouch_time = 0.0
                state = Estado.PULO
            else:
                crouch_condition = (
                    drop >= UPPER_CROUCH_DROP_THRESHOLD
                    and velocity < UPPER_CROUCH_MAX_UPWARD_VELOCITY
                )
                if crouch_condition:
                    if self._crouch_since is None:
                        self._crouch_since = timestamp_s
                    crouch_time = timestamp_s - self._crouch_since
                else:
                    self._crouch_since = None
                    crouch_time = 0.0

                if crouch_time >= UPPER_CROUCH_CONFIRM_SECONDS:
                    state = Estado.AGACHADO
                elif lateral <= -UPPER_LATERAL_THRESHOLD:
                    state = Estado.ESQUERDA
                elif lateral >= UPPER_LATERAL_THRESHOLD:
                    state = Estado.DIREITA
                else:
                    state = Estado.CENTRO

        self.debug = {
            "lateral": lateral,
            "lift": lift,
            "drop": drop,
            "velocity": velocity,
            "crouch_time": crouch_time,
            "crouch_candidate": 1.0 if (
                not arms_open
                and not jump_by_height
                and not jump_by_speed
                and drop >= UPPER_CROUCH_DROP_THRESHOLD
                and velocity < UPPER_CROUCH_MAX_UPWARD_VELOCITY
            ) else 0.0,
            "arms_visible": 1.0 if "arm_span" in features else 0.0,
            "arms_open": 1.0 if arms_open else 0.0,
            "arm_span": arm_span,
            "arm_min_side_extension": arm_min_side_extension,
            "arm_vertical_offset": arm_vertical_offset,
        }
        return state

    def limites_guias(self) -> dict[str, float] | None:
        if self.baseline is None:
            return None
        b = self.baseline
        return {
            "left_x": b["shoulder_x"] - b["shoulder_width"] * UPPER_LATERAL_THRESHOLD,
            "right_x": b["shoulder_x"] + b["shoulder_width"] * UPPER_LATERAL_THRESHOLD,
            "jump_y": b["shoulder_y"] - b["shoulder_width"] * UPPER_JUMP_LIFT_THRESHOLD,
            "neutral_y": b["shoulder_y"],
            "crouch_y": b["shoulder_y"] + b["shoulder_width"] * UPPER_CROUCH_DROP_THRESHOLD,
        }
```

## `config.py`

```python
"""Configuracoes centralizadas do projeto.

Ajuste os thresholds deste arquivo durante os testes de camera.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
POSE_MODEL_PATH = MODELS_DIR / "pose_landmarker_lite.task"
FACE_MODEL_PATH = MODELS_DIR / "face_landmarker.task"
GESTURE_MODEL_PATH = MODELS_DIR / "gesture_recognizer.task"

# Camera
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

# MediaPipe
MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
POSE_MIN_VISIBILITY = 0.35

# Calibracao
CALIBRATION_COUNTDOWN_SECONDS = 3.0
CALIBRATION_SAMPLES = 30

# Estabilizacao de estado
SMOOTHING_WINDOW = 5
MIN_STATE_VOTES = 3

# Modo MAOS: janela menor para responder rapido aos gestos.
HAND_SMOOTHING_WINDOW = 3
HAND_MIN_STATE_VOTES = 2

# Controle do jogo
COMMAND_COOLDOWN = 0.22
DOUBLE_LANE_COMMAND_INTERVAL = 0.12
REQUIRE_GAME_FOCUS = False
GAME_WINDOW_KEYWORDS = ("Subway Surfers", "Google Play Games")

# Modo CORPO
LATERAL_THRESHOLD = 0.45
JUMP_THRESHOLD = 0.18
CROUCH_HIP_THRESHOLD = 0.12
CROUCH_KNEE_ANGLE = 165.0
CROUCH_DEEP_HIP_THRESHOLD = 0.22

# Modo PEITORAL
UPPER_LATERAL_THRESHOLD = 0.45
UPPER_JUMP_LIFT_THRESHOLD = 0.25
UPPER_JUMP_MIN_LIFT_WITH_VELOCITY = 0.10
UPPER_JUMP_UPWARD_VELOCITY = 0.85
UPPER_CROUCH_DROP_THRESHOLD = 0.18
# Durante o agachamento, velocidade negativa significa que os ombros ainda estao
# descendo. Isso deve ser aceito. Apenas uma SUBIDA rapida cancela a confirmacao.
UPPER_CROUCH_MAX_UPWARD_VELOCITY = 0.45
UPPER_CROUCH_CONFIRM_SECONDS = 0.18

# Reinicio no modo PEITORAL: abrir os dois bracos aproximadamente na horizontal.
# ARM_SPAN = distancia entre pulsos / largura dos ombros.
UPPER_RESTART_ARM_SPAN_THRESHOLD = 3.00
# Cada pulso precisa ultrapassar lateralmente o ombro correspondente.
UPPER_RESTART_MIN_SIDE_EXTENSION = 0.60
# Tolerancia vertical dos pulsos em relacao a linha dos ombros.
UPPER_RESTART_MAX_VERTICAL_OFFSET = 0.95

# Modo ROSTO
FACE_YAW_DIRECTION = -1.0
FACE_PITCH_DIRECTION = -1.0
FACE_YAW_THRESHOLD_DEG = 20.0
FACE_PITCH_THRESHOLD_DEG = 15.0
FACE_ANGLE_SMOOTHING_ALPHA = 0.25

# Modo MAOS
# O Gesture Recognizer retorna Open_Palm e Closed_Fist com um score de 0 a 1.
HAND_GESTURE_MIN_SCORE = 0.55
HAND_HANDEDNESS_MIN_SCORE = 0.50
# Se a sua camera/driver fizer a lateralidade aparecer invertida no HUD,
# altere para True.
HAND_SWAP_SIDES = False

# Coracao com duas maos. O MediaPipe nao possui "Heart" entre os gestos prontos,
# portanto o projeto detecta a geometria usando os landmarks das duas maos.
# Distancias sao normalizadas pelo tamanho medio das maos.
HAND_HEART_CONTACT_RATIO = 0.75
HAND_HEART_MIN_OPENING_RATIO = 0.65
HAND_HEART_MIN_VERTICAL_GAP_RATIO = 0.35

# HUD / tela cheia
HUD_FONT_SCALE = 0.62
HUD_LINE_HEIGHT = 27
LANDMARK_RADIUS = 2
FULLSCREEN = True
HUD_SIDEBAR_MIN_WIDTH = 350
HUD_SIDEBAR_MAX_WIDTH = 455
```

## `controllers/__init__.py`

```python

```

## `controllers/game_controller.py`

```python
"""Envio de teclas globais para o jogo via pynput."""
from __future__ import annotations

import ctypes
import platform
import time
from threading import Lock

from pynput.keyboard import Controller, Key

from config import (
    COMMAND_COOLDOWN,
    DOUBLE_LANE_COMMAND_INTERVAL,
    GAME_WINDOW_KEYWORDS,
    REQUIRE_GAME_FOCUS,
)
from states import Estado


class GameController:
    """Converte comandos discretos em eventos reais de teclado."""

    KEY_HOLD_SECONDS = 0.055
    JUMP_KEY_HOLD_SECONDS = 0.120
    RESTART_KEY_HOLD_SECONDS = 0.100

    def __init__(self) -> None:
        self.keyboard = Controller()
        self._last_command_at: dict[Estado, float] = {}
        self._lock = Lock()
        self.last_sent_command: Estado | None = None

    @staticmethod
    def _foreground_window_title() -> str:
        if platform.system() != "Windows":
            return ""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def game_has_focus(self) -> bool:
        if not REQUIRE_GAME_FOCUS:
            return True
        if platform.system() != "Windows":
            return True
        title = self._foreground_window_title().lower()
        return any(keyword.lower() in title for keyword in GAME_WINDOW_KEYWORDS)

    def _press(self, state: Estado) -> None:
        key_map = {
            Estado.ESQUERDA: Key.left,
            Estado.DIREITA: Key.right,
            Estado.PULO: Key.up,
            Estado.AGACHADO: Key.down,
            Estado.REINICIAR: Key.f5,
        }

        key = key_map[state]
        if state == Estado.PULO:
            hold_seconds = self.JUMP_KEY_HOLD_SECONDS
        elif state == Estado.REINICIAR:
            hold_seconds = self.RESTART_KEY_HOLD_SECONDS
        else:
            hold_seconds = self.KEY_HOLD_SECONDS

        self.keyboard.press(key)
        time.sleep(hold_seconds)
        self.keyboard.release(key)

        self.last_sent_command = state
        key_name = "F5" if state == Estado.REINICIAR else state.value
        print(
            f"[TECLADO] {key_name} enviado "
            f"({hold_seconds * 1000:.0f} ms de pressionamento)",
            flush=True,
        )

    def send(self, commands: list[Estado]) -> bool:
        if not commands:
            return False

        if not self.game_has_focus():
            print("[TECLADO] comando ignorado: jogo sem foco.", flush=True)
            return False

        first = commands[0]
        now = time.perf_counter()
        last = self._last_command_at.get(first, -1e9)
        if now - last < COMMAND_COOLDOWN:
            print(
                f"[TECLADO] {first.value} ignorado pelo cooldown "
                f"({now - last:.3f}s < {COMMAND_COOLDOWN:.3f}s).",
                flush=True,
            )
            return False

        with self._lock:
            for i, command in enumerate(commands):
                self._press(command)
                if i < len(commands) - 1:
                    time.sleep(DOUBLE_LANE_COMMAND_INTERVAL)

            finished = time.perf_counter()
            for command in set(commands):
                self._last_command_at[command] = finished

        return True

    def reset_cooldowns(self) -> None:
        self._last_command_at.clear()
        self.last_sent_command = None
```

## `controllers/hand_gesture_manager.py`

```python
"""Gerencia gestos discretos do modo MAOS."""
from __future__ import annotations

from states import Estado


class HandGestureManager:
    """Gera um unico comando por entrada em cada gesto.

    Diferente de CORPO/PEITORAL/ROSTO, ESQUERDA e DIREITA aqui sao comandos
    relativos (um passo), nao a posicao fisica absoluta da pessoa.
    """

    ACTIONS = {
        Estado.ESQUERDA,
        Estado.DIREITA,
        Estado.PULO,
        Estado.AGACHADO,
        Estado.REINICIAR,
    }

    def __init__(self) -> None:
        self._last_action: Estado | None = None

    def reset(self) -> None:
        self._last_action = None

    def process(self, state: Estado) -> list[Estado]:
        if state in (Estado.CENTRO, Estado.SEM_POSE):
            self._last_action = None
            return []

        if state not in self.ACTIONS:
            return []

        if state == self._last_action:
            return []

        self._last_action = state
        return [state]
```

## `controllers/hotkeys.py`

```python
"""Atalhos globais F8/F10 usando pynput."""
from __future__ import annotations

from threading import Event

from pynput import keyboard


class GlobalHotkeys:
    def __init__(self) -> None:
        self.calibrate = Event()
        self.exit = Event()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key == keyboard.Key.f8:
            self.calibrate.set()
        elif key == keyboard.Key.f10:
            self.exit.set()

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()

    @staticmethod
    def consume(event: Event) -> bool:
        if event.is_set():
            event.clear()
            return True
        return False
```

## `controllers/transition_manager.py`

```python
"""Transforma estados fisicos em comandos discretos de jogo."""
from __future__ import annotations

from states import Estado, ESTADOS_LATERAIS, ESTADOS_MOMENTANEOS


class TransitionManager:
    def __init__(self) -> None:
        self.faixa_lateral = Estado.CENTRO
        self._ultimo_estado_momentaneo: Estado | None = None

    def reset(self) -> None:
        self.faixa_lateral = Estado.CENTRO
        self._ultimo_estado_momentaneo = None

    @staticmethod
    def _lane_index(state: Estado) -> int:
        return {
            Estado.ESQUERDA: -1,
            Estado.CENTRO: 0,
            Estado.DIREITA: 1,
        }[state]

    def process(self, state: Estado) -> list[Estado]:
        if state == Estado.SEM_POSE:
            return []

        # PULO, AGACHADO e REINICIAR sao eventos momentaneos. Nenhum deles muda
        # a faixa lateral interna.
        if state in ESTADOS_MOMENTANEOS:
            if self._ultimo_estado_momentaneo == state:
                return []
            self._ultimo_estado_momentaneo = state
            return [state]

        self._ultimo_estado_momentaneo = None

        if state not in ESTADOS_LATERAIS:
            return []

        old_idx = self._lane_index(self.faixa_lateral)
        new_idx = self._lane_index(state)
        delta = new_idx - old_idx
        self.faixa_lateral = state

        if delta == 0:
            return []
        command = Estado.DIREITA if delta > 0 else Estado.ESQUERDA
        return [command] * abs(delta)
```

## `download_models.py`

```python
"""Baixa os modelos oficiais do MediaPipe usados pelo projeto."""
from pathlib import Path
from urllib.request import urlretrieve

MODELS = {
    "pose_landmarker_lite.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
    "gesture_recognizer.task": (
        "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
        "gesture_recognizer/float16/1/gesture_recognizer.task"
    ),
}


def main() -> None:
    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(exist_ok=True)

    for filename, url in MODELS.items():
        destination = models_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            print(f"[OK] Ja existe: {destination}")
            continue
        print(f"Baixando {filename}...")
        urlretrieve(url, destination)
        print(f"[OK] Salvo em {destination}")


if __name__ == "__main__":
    main()
```

## `keyboard_test_receiver.py`

```python
"""Receptor simples para testar os comandos sem abrir o jogo.

Execute este arquivo em outro terminal. Ele imprime LEFT/RIGHT/UP/DOWN/F5 ao
receber os eventos globais gerados pelo controlador.
"""
from pynput import keyboard


def on_press(key):
    mapping = {
        keyboard.Key.left: "LEFT",
        keyboard.Key.right: "RIGHT",
        keyboard.Key.up: "UP",
        keyboard.Key.down: "DOWN",
        keyboard.Key.f5: "F5 / REINICIAR",
    }
    if key in mapping:
        print(f"Recebido: {mapping[key]}")
    elif key == keyboard.Key.esc:
        print("Encerrando receptor.")
        return False
    return None


if __name__ == "__main__":
    print("Aguardando setas e F5 globais. Pressione ESC para sair.")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
```

## `main.py`

```python
from __future__ import annotations

import ctypes
import platform
import sys
import time
from typing import Any

import cv2

from calibration.calibrator import Calibrator
from classifiers.body_classifier import BodyClassifier
from classifiers.face_classifier import FaceClassifier
from classifiers.hand_classifier import HandClassifier
from classifiers.stabilizer import StateStabilizer
from classifiers.upper_body_classifier import UpperBodyClassifier
from config import (
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    FACE_MODEL_PATH,
    FULLSCREEN,
    GESTURE_MODEL_PATH,
    HAND_MIN_STATE_VOTES,
    HAND_SMOOTHING_WINDOW,
    POSE_MODEL_PATH,
)
from controllers.game_controller import GameController
from controllers.hand_gesture_manager import HandGestureManager
from controllers.hotkeys import GlobalHotkeys
from controllers.transition_manager import TransitionManager
from states import Estado
from vision.face_detector import FaceDetector
from vision.hand_detector import HandDetector
from vision.hud import draw_face, draw_guides, draw_hands, draw_hud, draw_pose
from vision.pose_detector import PoseDetector


MODES = {"1": "CORPO", "2": "PEITORAL", "3": "ROSTO", "4": "MAOS"}


def choose_mode() -> str:
    print("\nEscolha o modo de controle:\n")
    print("1 - CORPO")
    print("2 - PEITORAL")
    print("3 - ROSTO")
    print("4 - MAOS")
    while True:
        option = input("\nModo: ").strip()
        if option in MODES:
            return MODES[option]
        print("Opcao invalida. Digite 1, 2, 3 ou 4.")


def open_camera() -> cv2.VideoCapture:
    if platform.system() == "Windows":
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(CAMERA_INDEX)
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError(
            f"Nao foi possivel abrir a camera CAMERA_INDEX={CAMERA_INDEX}. "
            "Altere CAMERA_INDEX em config.py."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def get_display_size() -> tuple[int, int]:
    """Retorna a resolucao principal para montar o dashboard em tela cheia."""
    if platform.system() == "Windows":
        try:
            user32 = ctypes.windll.user32
            return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
        except Exception:
            pass
    return 1600, 900


def build_mode(mode: str) -> tuple[Any, Any]:
    if mode == "CORPO":
        return PoseDetector(POSE_MODEL_PATH), BodyClassifier()
    if mode == "PEITORAL":
        return PoseDetector(POSE_MODEL_PATH), UpperBodyClassifier()
    if mode == "ROSTO":
        return FaceDetector(FACE_MODEL_PATH), FaceClassifier()
    return HandDetector(GESTURE_MODEL_PATH), HandClassifier()


def reset_for_calibration(
    classifier: Any,
    stabilizer: StateStabilizer,
    transition_manager: TransitionManager,
    game_controller: GameController,
    calibrator: Calibrator,
) -> None:
    classifier.reset()
    stabilizer.reset(Estado.CENTRO)
    transition_manager.reset()
    game_controller.reset_cooldowns()
    calibrator.start()


def reset_hand_mode(
    classifier: HandClassifier,
    stabilizer: StateStabilizer,
    hand_manager: HandGestureManager,
    game_controller: GameController,
    calibrator: Calibrator,
) -> None:
    classifier.reset()
    stabilizer.reset(Estado.CENTRO)
    hand_manager.reset()
    game_controller.reset_cooldowns()
    # O Gesture Recognizer nao precisa de baseline geometrica.
    calibrator.active = False
    calibrator.complete = True
    calibrator.baseline = {}
    calibrator.samples.clear()


def main() -> int:
    mode = choose_mode()
    hand_mode = mode == "MAOS"

    print(f"\nModo selecionado: {mode}")
    if hand_mode:
        print("O modo MAOS nao precisa de calibracao geometrica.")
        print("F8 reinicia os gestos | controle ativo automaticamente | F10 encerra\n")
    else:
        print("A calibracao inicial comecara automaticamente.")
        print("F8 recalibra | controle do jogo ativa automaticamente apos calibrar | F10 encerra\n")

    try:
        detector, classifier = build_mode(mode)
        cap = open_camera()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    if hand_mode:
        stabilizer = StateStabilizer(
            window_size=HAND_SMOOTHING_WINDOW,
            min_votes=HAND_MIN_STATE_VOTES,
        )
    else:
        stabilizer = StateStabilizer()

    transition_manager = TransitionManager()
    hand_manager = HandGestureManager()
    game_controller = GameController()
    hotkeys = GlobalHotkeys()
    calibrator = Calibrator()

    if hand_mode:
        reset_hand_mode(classifier, stabilizer, hand_manager, game_controller, calibrator)
        game_enabled = True
    else:
        game_enabled = False
        reset_for_calibration(classifier, stabilizer, transition_manager, game_controller, calibrator)

    hotkeys.start()

    last_frame_time = time.perf_counter()
    fps_smoothed = 0.0
    start_time = time.perf_counter()
    last_timestamp_ms = -1
    state = Estado.CENTRO
    window_name = "Subway Vision Controller"
    display_size = get_display_size()
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    if FULLSCREEN:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while cap.isOpened():
            if GlobalHotkeys.consume(hotkeys.exit):
                break

            if GlobalHotkeys.consume(hotkeys.calibrate):
                if hand_mode:
                    reset_hand_mode(classifier, stabilizer, hand_manager, game_controller, calibrator)
                    game_enabled = True
                else:
                    game_enabled = False
                    reset_for_calibration(
                        classifier, stabilizer, transition_manager, game_controller, calibrator
                    )

            ok, frame = cap.read()
            if not ok or frame is None:
                print("ERRO: falha ao capturar frame da webcam.")
                break

            frame = cv2.flip(frame, 1)
            now = time.perf_counter()
            timestamp_ms = int((now - start_time) * 1000.0)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms

            detected = detector.detect(frame, timestamp_ms)

            if mode == "ROSTO":
                face_data = detected
                landmarks = face_data.get("landmarks") if face_data else None
                features = classifier.extrair_features(face_data)
                draw_face(frame, landmarks)
            elif mode == "MAOS":
                hand_data = detected
                features = None
                draw_hands(frame, hand_data)
            else:
                landmarks = detected
                features = classifier.extrair_features(landmarks)
                draw_pose(frame, landmarks)

            if hand_mode:
                raw_state = classifier.classificar(hand_data, now)
                state = stabilizer.update(raw_state)

                if game_enabled and game_controller.game_has_focus():
                    # No modo MAOS cada gesto e um comando relativo de uma etapa.
                    commands = hand_manager.process(state)
                    game_controller.send(commands)
            elif calibrator.active:
                baseline = calibrator.update(features)
                state = Estado.SEM_POSE if features is None else Estado.CENTRO
                if baseline is not None:
                    classifier.definir_baseline(baseline)
                    stabilizer.reset(Estado.CENTRO)
                    transition_manager.reset()
                    game_controller.reset_cooldowns()
                    game_enabled = True
                    state = Estado.CENTRO
            elif calibrator.complete:
                raw_state = classifier.classificar(features, now)
                state = stabilizer.update(raw_state)

                if (
                    game_enabled
                    and state != Estado.SEM_POSE
                    and game_controller.game_has_focus()
                ):
                    commands = transition_manager.process(state)
                    game_controller.send(commands)
            else:
                state = Estado.SEM_POSE if features is None else Estado.CENTRO

            if calibrator.complete and not hand_mode:
                draw_guides(frame, mode, classifier)

            dt = max(now - last_frame_time, 1e-6)
            instant_fps = 1.0 / dt
            fps_smoothed = (
                instant_fps
                if fps_smoothed == 0
                else (0.90 * fps_smoothed + 0.10 * instant_fps)
            )
            last_frame_time = now

            calibration_message = (
                "MAOS: CALIBRACAO NAO NECESSARIA"
                if hand_mode
                else calibrator.message()
            )

            display_frame = draw_hud(
                frame=frame,
                mode=mode,
                state=state,
                fps=fps_smoothed,
                game_enabled=game_enabled,
                calibrated=calibrator.complete,
                calibration_message=calibration_message,
                classifier=classifier,
                display_size=display_size,
            )

            cv2.imshow(window_name, display_frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except KeyboardInterrupt:
        pass
    finally:
        hotkeys.stop()
        cap.release()
        detector.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `models/README.md`

```markdown
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
```

## `requirements.txt`

```text
# Recomendado: Python 3.11 (64 bits)
mediapipe==1.0.1
opencv-python>=4.10,<5
numpy>=1.26,<3
pynput>=1.7.7,<2
```

## `run.bat`

```text
@echo off
python main.py
pause
```

## `states.py`

```python
from enum import Enum


class Estado(str, Enum):
    CENTRO = "CENTRO"
    ESQUERDA = "ESQUERDA"
    DIREITA = "DIREITA"
    PULO = "PULO"
    AGACHADO = "AGACHADO"
    REINICIAR = "REINICIAR"
    SEM_POSE = "SEM_POSE"


ESTADOS_LATERAIS = {Estado.ESQUERDA, Estado.CENTRO, Estado.DIREITA}
ESTADOS_MOMENTANEOS = {Estado.PULO, Estado.AGACHADO, Estado.REINICIAR}
```

## `tests/test_hands.py`

```python
import unittest
from types import SimpleNamespace

from classifiers.hand_classifier import HandClassifier
from controllers.hand_gesture_manager import HandGestureManager
from states import Estado


def lm(x=0.0, y=0.0):
    return SimpleNamespace(x=x, y=y)


def plain_landmarks(cx: float):
    points = [lm(cx, 0.60) for _ in range(21)]
    points[0] = lm(cx, 0.60)
    points[5] = lm(cx - 0.03, 0.52)
    points[9] = lm(cx, 0.50)
    points[17] = lm(cx + 0.03, 0.52)
    return points


def heart_landmarks(side: str):
    cx = 0.33 if side == "LEFT" else 0.67
    points = plain_landmarks(cx)
    if side == "LEFT":
        points[8] = lm(0.49, 0.40)  # indicador toca o da outra mao
        points[4] = lm(0.48, 0.50)  # polegar toca o da outra mao
    else:
        points[8] = lm(0.51, 0.40)
        points[4] = lm(0.52, 0.50)
    return points


def hand(side: str, gesture: str, score: float = 0.95, landmarks=None):
    return {
        "side": side,
        "gesture": gesture,
        "gesture_score": score,
        "side_score": 0.99,
        "landmarks": landmarks if landmarks is not None else plain_landmarks(0.35 if side == "LEFT" else 0.65),
    }


class HandClassifierTests(unittest.TestCase):
    def setUp(self):
        self.c = HandClassifier()

    def classify(self, *hands):
        return self.c.classificar({"hands": list(hands)})

    def test_left_open(self):
        self.assertEqual(self.classify(hand("LEFT", "Open_Palm")), Estado.ESQUERDA)

    def test_right_open(self):
        self.assertEqual(self.classify(hand("RIGHT", "Open_Palm")), Estado.DIREITA)

    def test_both_open_jump(self):
        self.assertEqual(
            self.classify(hand("LEFT", "Open_Palm"), hand("RIGHT", "Open_Palm")),
            Estado.PULO,
        )

    def test_both_closed_crouch(self):
        self.assertEqual(
            self.classify(hand("LEFT", "Closed_Fist"), hand("RIGHT", "Closed_Fist")),
            Estado.AGACHADO,
        )

    def test_heart_restarts(self):
        self.assertEqual(
            self.classify(
                hand("LEFT", "None", landmarks=heart_landmarks("LEFT")),
                hand("RIGHT", "None", landmarks=heart_landmarks("RIGHT")),
            ),
            Estado.REINICIAR,
        )
        self.assertEqual(self.c.debug["heart_detected"], 1.0)

    def test_one_closed_is_neutral(self):
        self.assertEqual(self.classify(hand("LEFT", "Closed_Fist")), Estado.CENTRO)

    def test_no_hands_is_sem_pose(self):
        self.assertEqual(self.classify(), Estado.SEM_POSE)

    def test_low_score_is_not_action(self):
        self.assertEqual(self.classify(hand("LEFT", "Open_Palm", 0.2)), Estado.CENTRO)


class HandGestureManagerTests(unittest.TestCase):
    def test_holding_does_not_repeat(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(m.process(Estado.ESQUERDA), [])

    def test_release_rearms_same_gesture(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.PULO), [Estado.PULO])
        self.assertEqual(m.process(Estado.CENTRO), [])
        self.assertEqual(m.process(Estado.PULO), [Estado.PULO])

    def test_restart_is_edge_triggered(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.REINICIAR), [Estado.REINICIAR])
        self.assertEqual(m.process(Estado.REINICIAR), [])
        self.assertEqual(m.process(Estado.CENTRO), [])
        self.assertEqual(m.process(Estado.REINICIAR), [Estado.REINICIAR])

    def test_switch_gesture_sends_one_each(self):
        m = HandGestureManager()
        self.assertEqual(m.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(m.process(Estado.DIREITA), [Estado.DIREITA])


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_logic.py`

```python
import unittest
from unittest.mock import patch

from calibration.calibrator import Calibrator
from classifiers.body_classifier import BodyClassifier
from classifiers.stabilizer import StateStabilizer
from classifiers.upper_body_classifier import UpperBodyClassifier
from controllers.transition_manager import TransitionManager
from states import Estado


class TransitionManagerTests(unittest.TestCase):
    def test_center_to_left(self):
        t = TransitionManager()
        self.assertEqual(t.process(Estado.ESQUERDA), [Estado.ESQUERDA])
        self.assertEqual(t.process(Estado.ESQUERDA), [])

    def test_left_to_center_sends_right(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.CENTRO), [Estado.DIREITA])

    def test_center_to_right(self):
        t = TransitionManager()
        self.assertEqual(t.process(Estado.DIREITA), [Estado.DIREITA])
        self.assertEqual(t.process(Estado.DIREITA), [])

    def test_right_to_center_sends_left(self):
        t = TransitionManager()
        t.process(Estado.DIREITA)
        self.assertEqual(t.process(Estado.CENTRO), [Estado.ESQUERDA])

    def test_two_lane_transition(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.DIREITA), [Estado.DIREITA, Estado.DIREITA])
        self.assertEqual(t.process(Estado.ESQUERDA), [Estado.ESQUERDA, Estado.ESQUERDA])

    def test_vertical_does_not_change_lane_and_is_edge_triggered(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.PULO), [Estado.PULO])
        self.assertEqual(t.process(Estado.PULO), [])
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.ESQUERDA), [])

    def test_sem_pose_does_not_change_lane(self):
        t = TransitionManager()
        t.process(Estado.DIREITA)
        self.assertEqual(t.process(Estado.SEM_POSE), [])
        self.assertEqual(t.faixa_lateral, Estado.DIREITA)

    def test_restart_is_edge_triggered_and_keeps_lane(self):
        t = TransitionManager()
        t.process(Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.REINICIAR), [Estado.REINICIAR])
        self.assertEqual(t.process(Estado.REINICIAR), [])
        self.assertEqual(t.faixa_lateral, Estado.ESQUERDA)
        self.assertEqual(t.process(Estado.ESQUERDA), [])
        self.assertEqual(t.process(Estado.REINICIAR), [Estado.REINICIAR])


class StabilizerTests(unittest.TestCase):
    def test_single_outlier_does_not_change_state(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        for state in [Estado.CENTRO, Estado.CENTRO, Estado.DIREITA, Estado.CENTRO, Estado.CENTRO]:
            result = s.update(state)
        self.assertEqual(result, Estado.CENTRO)

    def test_sem_pose_is_not_added_to_history(self):
        s = StateStabilizer(window_size=3, min_votes=2)
        s.update(Estado.ESQUERDA)
        s.update(Estado.ESQUERDA)
        self.assertEqual(s.update(Estado.SEM_POSE), Estado.SEM_POSE)
        self.assertEqual(s.stable_state, Estado.ESQUERDA)

    def test_jump_is_confirmed_with_two_votes_in_three_frames(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        s.update(Estado.CENTRO)
        s.update(Estado.CENTRO)
        self.assertNotEqual(s.update(Estado.PULO), Estado.PULO)
        self.assertEqual(s.update(Estado.PULO), Estado.PULO)

    def test_single_jump_frame_is_filtered(self):
        s = StateStabilizer(window_size=5, min_votes=3)
        s.update(Estado.CENTRO)
        s.update(Estado.CENTRO)
        self.assertNotEqual(s.update(Estado.PULO), Estado.PULO)
        self.assertNotEqual(s.update(Estado.CENTRO), Estado.PULO)


class CrouchRecognitionTests(unittest.TestCase):
    def test_upper_body_accepts_descent_and_confirms_crouch(self):
        c = UpperBodyClassifier()
        c.definir_baseline({
            "shoulder_x": 0.50,
            "shoulder_y": 0.50,
            "shoulder_width": 0.20,
        })

        # Cruza o limiar de agachamento ainda descendo.
        first = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.54,
            "shoulder_width": 0.20,
        }, 1.00)
        self.assertNotEqual(first, Estado.AGACHADO)

        # Continua descendo; a velocidade e negativa e deve ser aceita.
        second = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.55,
            "shoulder_width": 0.20,
        }, 1.20)
        self.assertEqual(second, Estado.AGACHADO)

    def test_upper_body_open_arms_restarts(self):
        c = UpperBodyClassifier()
        c.definir_baseline({
            "shoulder_x": 0.50,
            "shoulder_y": 0.40,
            "shoulder_width": 0.20,
        })
        state = c.classificar({
            "shoulder_x": 0.50,
            "shoulder_y": 0.40,
            "shoulder_width": 0.20,
            "arm_span": 3.40,
            "arm_min_side_extension": 0.75,
            "arm_vertical_offset": 0.20,
        }, 1.0)
        self.assertEqual(state, Estado.REINICIAR)
        self.assertEqual(c.debug["arms_open"], 1.0)

    def test_body_deep_crouch_does_not_depend_only_on_knee_angle(self):
        c = BodyClassifier()
        c.definir_baseline({
            "torso_x": 0.50,
            "hip_x": 0.50,
            "hip_y": 0.50,
            "ankle_y": 0.90,
            "shoulder_width": 0.20,
            "torso_height": 0.20,
            "left_knee_angle": 180.0,
            "right_knee_angle": 180.0,
        })
        state = c.classificar({
            "torso_x": 0.50,
            "hip_x": 0.50,
            "hip_y": 0.55,  # queda de 0.25 torso_height: agachamento profundo
            "ankle_y": 0.90,
            "shoulder_width": 0.20,
            "torso_height": 0.20,
            "left_knee_angle": 175.0,
            "right_knee_angle": 175.0,
        }, 1.0)
        self.assertEqual(state, Estado.AGACHADO)


class CalibratorTests(unittest.TestCase):
    def test_uses_median(self):
        c = Calibrator(countdown_seconds=0.0, sample_count=5)
        with patch("calibration.calibrator.time.perf_counter", return_value=10.0):
            c.start()
            baseline = None
            for value in [1.0, 1.1, 50.0, 0.9, 1.0]:
                baseline = c.update({"x": value}) or baseline
        self.assertIsNotNone(baseline)
        self.assertAlmostEqual(baseline["x"], 1.0)


if __name__ == "__main__":
    unittest.main()
```

## `vision/__init__.py`

```python

```

## `vision/face_detector.py`

```python
"""Wrapper do MediaPipe Face Landmarker."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from config import (
    MIN_DETECTION_CONFIDENCE,
    MIN_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)


class FaceDetector:
    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo Face Landmarker nao encontrado: {model_path}. "
                "Baixe face_landmarker.task e coloque em models/."
            )

        model_bytes = model_path.read_bytes()
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_face_presence_confidence=MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame_bgr: Any, timestamp_ms: int) -> dict[str, Any] | None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return None

        matrix = None
        if result.facial_transformation_matrixes:
            matrix = result.facial_transformation_matrixes[0]

        return {
            "landmarks": result.face_landmarks[0],
            "matrix": matrix,
        }

    def close(self) -> None:
        self._landmarker.close()
```

## `vision/hand_detector.py`

```python
"""Deteccao de duas maos e reconhecimento de gestos com MediaPipe Tasks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from config import (
    HAND_HANDEDNESS_MIN_SCORE,
    HAND_SWAP_SIDES,
    MIN_DETECTION_CONFIDENCE,
    MIN_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)


class HandDetector:
    """Reconhece gestos e landmarks de ate duas maos em modo VIDEO."""

    def __init__(self, model_path: Path) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo de gestos nao encontrado: {model_path}. "
                "Execute: python download_models.py"
            )

        model_bytes = model_path.read_bytes()
        if not model_bytes:
            raise ValueError(f"Modelo de gestos vazio ou invalido: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_buffer=model_bytes)
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
        )
        self._recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

    @staticmethod
    def _swap_side(side: str) -> str:
        if not HAND_SWAP_SIDES:
            return side
        if side == "LEFT":
            return "RIGHT"
        if side == "RIGHT":
            return "LEFT"
        return side

    def detect(self, frame_bgr: Any, timestamp_ms: int) -> dict[str, Any]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._recognizer.recognize_for_video(image, timestamp_ms)

        hands: list[dict[str, Any]] = []
        hand_landmarks = result.hand_landmarks or []
        handedness_list = result.handedness or []
        gestures_list = result.gestures or []
        # Para o coracao precisamos dos landmarks mesmo quando o classificador
        # de gestos nao devolve uma categoria util para aquela mao.
        count = min(len(hand_landmarks), len(handedness_list))

        for index in range(count):
            side = "UNKNOWN"
            side_score = 0.0
            if handedness_list[index]:
                handedness = handedness_list[index][0]
                side = str(handedness.category_name or "UNKNOWN").upper()
                side_score = float(handedness.score or 0.0)
                if side_score < HAND_HANDEDNESS_MIN_SCORE:
                    side = "UNKNOWN"
                side = self._swap_side(side)

            gesture = "None"
            gesture_score = 0.0
            if index < len(gestures_list) and gestures_list[index]:
                category = gestures_list[index][0]
                gesture = str(category.category_name or "None")
                gesture_score = float(category.score or 0.0)

            hands.append(
                {
                    "side": side,
                    "side_score": side_score,
                    "gesture": gesture,
                    "gesture_score": gesture_score,
                    "landmarks": hand_landmarks[index],
                }
            )

        return {"hands": hands}

    def close(self) -> None:
        self._recognizer.close()
```

## `vision/hud.py`

```python
"""HUD em tela cheia, landmarks e guias visuais."""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from config import (
    CROUCH_DEEP_HIP_THRESHOLD,
    CROUCH_HIP_THRESHOLD,
    CROUCH_KNEE_ANGLE,
    FACE_PITCH_THRESHOLD_DEG,
    FACE_YAW_THRESHOLD_DEG,
    HAND_GESTURE_MIN_SCORE,
    HAND_HEART_CONTACT_RATIO,
    HAND_HEART_MIN_VERTICAL_GAP_RATIO,
    HUD_SIDEBAR_MAX_WIDTH,
    HUD_SIDEBAR_MIN_WIDTH,
    JUMP_THRESHOLD,
    LANDMARK_RADIUS,
    LATERAL_THRESHOLD,
    UPPER_CROUCH_CONFIRM_SECONDS,
    UPPER_CROUCH_DROP_THRESHOLD,
    UPPER_CROUCH_MAX_UPWARD_VELOCITY,
    UPPER_JUMP_LIFT_THRESHOLD,
    UPPER_JUMP_UPWARD_VELOCITY,
    UPPER_LATERAL_THRESHOLD,
    UPPER_RESTART_ARM_SPAN_THRESHOLD,
    UPPER_RESTART_MAX_VERTICAL_OFFSET,
    UPPER_RESTART_MIN_SIDE_EXTENSION,
)
from states import Estado


# BGR
BG = (20, 23, 29)
PANEL = (31, 35, 43)
PANEL_2 = (39, 44, 53)
BORDER = (62, 69, 82)
TEXT = (240, 243, 247)
MUTED = (162, 170, 184)
ACCENT = (86, 199, 122)
CYAN = (224, 183, 72)
YELLOW = (73, 208, 245)
RED = (92, 92, 232)
PURPLE = (208, 117, 187)

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def draw_pose(frame: Any, landmarks: list[Any] | None) -> None:
    if not landmarks:
        return
    h, w = frame.shape[:2]
    for a, b in POSE_CONNECTIONS:
        if a < len(landmarks) and b < len(landmarks):
            pa = (int(landmarks[a].x * w), int(landmarks[a].y * h))
            pb = (int(landmarks[b].x * w), int(landmarks[b].y * h))
            cv2.line(frame, pa, pb, ACCENT, 2, cv2.LINE_AA)
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(frame, (x, y), LANDMARK_RADIUS, YELLOW, -1, cv2.LINE_AA)


def draw_face(frame: Any, landmarks: list[Any] | None) -> None:
    if not landmarks:
        return
    h, w = frame.shape[:2]
    for i, lm in enumerate(landmarks):
        if i % 5 != 0:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(frame, (x, y), 1, YELLOW, -1, cv2.LINE_AA)


def draw_hands(frame: Any, hand_data: dict[str, Any] | None) -> None:
    if not hand_data:
        return
    h, w = frame.shape[:2]
    for hand in hand_data.get("hands", []):
        landmarks = hand.get("landmarks") or []
        for a, b in HAND_CONNECTIONS:
            if a < len(landmarks) and b < len(landmarks):
                pa = (int(landmarks[a].x * w), int(landmarks[a].y * h))
                pb = (int(landmarks[b].x * w), int(landmarks[b].y * h))
                cv2.line(frame, pa, pb, ACCENT, 2, cv2.LINE_AA)
        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            if 0 <= x < w and 0 <= y < h:
                cv2.circle(frame, (x, y), LANDMARK_RADIUS + 1, YELLOW, -1, cv2.LINE_AA)

        if landmarks:
            wrist = landmarks[0]
            x, y = int(wrist.x * w), int(wrist.y * h)
            side = hand.get("side", "?")
            gesture = hand.get("gesture", "None")
            score = float(hand.get("gesture_score", 0.0))
            label = f"{side}: {gesture} {score:.2f}"
            _shadow_text(frame, label, (max(5, x - 80), max(20, y - 15)), 0.48)


def _shadow_text(
    image: np.ndarray,
    text: str,
    org: tuple[int, int],
    scale: float,
    color: tuple[int, int, int] = TEXT,
    thickness: int = 1,
) -> None:
    cv2.putText(image, text, (org[0] + 1, org[1] + 1), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def _rounded_rect(
    image: np.ndarray,
    p1: tuple[int, int],
    p2: tuple[int, int],
    color: tuple[int, int, int],
    radius: int = 18,
    thickness: int = -1,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    radius = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if thickness != -1:
        cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, thickness, cv2.LINE_AA)
        cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(image, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness, cv2.LINE_AA)
        return

    cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    cv2.circle(image, (x1 + radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x2 - radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x1 + radius, y2 - radius), radius, color, -1, cv2.LINE_AA)
    cv2.circle(image, (x2 - radius, y2 - radius), radius, color, -1, cv2.LINE_AA)


def _vline(frame: Any, x_norm: float, label: str) -> None:
    h, w = frame.shape[:2]
    x = int(x_norm * w)
    cv2.line(frame, (x, 0), (x, h), CYAN, 1, cv2.LINE_AA)
    _shadow_text(frame, label, (max(5, x - 45), h - 18), 0.5)


def _hline(frame: Any, y_norm: float, label: str) -> None:
    h, w = frame.shape[:2]
    y = int(y_norm * h)
    cv2.line(frame, (0, y), (w, y), YELLOW, 1, cv2.LINE_AA)
    _shadow_text(frame, label, (w - 185, max(20, y - 6)), 0.5)


def draw_guides(frame: Any, mode: str, classifier: Any) -> None:
    guides = classifier.limites_guias() if hasattr(classifier, "limites_guias") else None
    if mode in {"CORPO", "PEITORAL"} and guides:
        _vline(frame, guides["left_x"], "ESQUERDA")
        _vline(frame, guides["right_x"], "DIREITA")
        h, w = frame.shape[:2]
        _shadow_text(frame, "CENTRO", (w // 2 - 40, h - 18), 0.5)

    if mode == "PEITORAL" and guides:
        _hline(frame, guides["jump_y"], "PULO")
        _hline(frame, guides["neutral_y"], "NEUTRO")
        _hline(frame, guides["crouch_y"], "AGACHADO")

    if mode == "ROSTO":
        h, w = frame.shape[:2]
        cx, cy = w - 155, 150
        cv2.rectangle(frame, (cx - 110, cy - 58), (cx + 110, cy + 58), CYAN, 1)
        _shadow_text(frame, "CENTRO", (cx - 35, cy + 5), 0.5)
        _shadow_text(frame, "ESQUERDA", (cx - 108, cy - 72), 0.45)
        _shadow_text(frame, "DIREITA", (cx + 44, cy - 72), 0.45)
        _shadow_text(frame, "PULO", (cx - 22, cy - 74), 0.45)
        _shadow_text(frame, "AGACHADO", (cx - 40, cy + 80), 0.45)


def _state_color(state: Estado) -> tuple[int, int, int]:
    return {
        Estado.CENTRO: CYAN,
        Estado.ESQUERDA: YELLOW,
        Estado.DIREITA: YELLOW,
        Estado.PULO: ACCENT,
        Estado.AGACHADO: PURPLE,
        Estado.REINICIAR: (68, 165, 245),
        Estado.SEM_POSE: RED,
    }.get(state, TEXT)


def _fit_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(width / max(w, 1), height / max(h, 1))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)


def _draw_card_title(canvas: np.ndarray, x: int, y: int, title: str) -> None:
    _shadow_text(canvas, title, (x, y), 0.55, MUTED, 1)


def _draw_lines(
    canvas: np.ndarray,
    lines: list[str],
    x: int,
    y: int,
    max_width: int,
    line_height: int = 28,
    scale: float = 0.52,
) -> int:
    yy = y
    for line in lines:
        # Quebra simples para evitar estourar o painel em resolucoes menores.
        pieces = [line]
        if cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > max_width:
            words = line.split()
            pieces = []
            current = ""
            for word in words:
                candidate = (current + " " + word).strip()
                if current and cv2.getTextSize(candidate, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > max_width:
                    pieces.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                pieces.append(current)
        for piece in pieces:
            _shadow_text(canvas, piece, (x, yy), scale, TEXT, 1)
            yy += line_height
    return yy


def _mode_help(mode: str) -> list[str]:
    if mode == "CORPO":
        return [
            "Mover corpo: esquerda / direita",
            "Pular: subir corpo",
            "Agachar: abaixar quadril",
        ]
    if mode == "PEITORAL":
        return [
            "Mover tronco: esquerda / direita",
            "Subir ombros: pular",
            "Descer ombros: agachar",
            "Abrir os 2 bracos: F5 / reiniciar",
        ]
    if mode == "ROSTO":
        return [
            "Virar cabeca: esquerda / direita",
            "Olhar para cima: pular",
            "Olhar para baixo: agachar",
        ]
    return [
        "Palma esquerda: esquerda",
        "Palma direita: direita",
        "2 palmas abertas: pular",
        "2 punhos fechados: agachar",
        "Coracao com 2 maos: F5 / reiniciar",
    ]


def _debug_lines(mode: str, classifier: Any) -> list[str]:
    d = getattr(classifier, "debug", {}) or {}
    if not d:
        return ["Aguardando dados..."]

    if mode == "CORPO":
        return [
            f"Lateral  {d.get('lateral', 0):+.2f} / {LATERAL_THRESHOLD:.2f}",
            f"Pulo     {d.get('jump_score', 0):+.2f} / {JUMP_THRESHOLD:.2f}",
            f"Quadril  {d.get('hip_drop', 0):+.2f} / {CROUCH_HIP_THRESHOLD:.2f}",
            f"Joelho   {d.get('knee_angle', 0):.1f} / {CROUCH_KNEE_ANGLE:.0f}",
            f"Profundo {d.get('hip_drop', 0):+.2f} / {CROUCH_DEEP_HIP_THRESHOLD:.2f}",
        ]
    if mode == "PEITORAL":
        arms = "ABERTOS" if d.get("arms_open", 0) >= 0.5 else "normal"
        if d.get("arms_visible", 0) < 0.5:
            arms = "pulsos nao visiveis"
        return [
            f"Lateral     {d.get('lateral', 0):+.2f} / {UPPER_LATERAL_THRESHOLD:.2f}",
            f"Subida      {d.get('lift', 0):+.2f} / {UPPER_JUMP_LIFT_THRESHOLD:.2f}",
            f"Descida     {d.get('drop', 0):+.2f} / {UPPER_CROUCH_DROP_THRESHOLD:.2f}",
            f"Velocidade  {d.get('velocity', 0):+.2f} / {UPPER_JUMP_UPWARD_VELOCITY:.2f}",
            f"Agachado    {d.get('crouch_time', 0):.2f}s / {UPPER_CROUCH_CONFIRM_SECONDS:.2f}s",
            f"Bracos      {arms}",
            f"Span        {d.get('arm_span', 0):.2f} / {UPPER_RESTART_ARM_SPAN_THRESHOLD:.2f}",
            f"Ext. lateral {d.get('arm_min_side_extension', 0):.2f} / {UPPER_RESTART_MIN_SIDE_EXTENSION:.2f}",
            f"Altura braco {d.get('arm_vertical_offset', 0):.2f} <= {UPPER_RESTART_MAX_VERTICAL_OFFSET:.2f}",
        ]
    if mode == "ROSTO":
        return [
            f"Yaw    {d.get('yaw', 0):+.1f} / {FACE_YAW_THRESHOLD_DEG:.0f}",
            f"Pitch  {d.get('pitch', 0):+.1f} / {FACE_PITCH_THRESHOLD_DEG:.0f}",
        ]

    heart = "DETECTADO" if d.get("heart_detected", 0) >= 0.5 else "nao"
    return [
        f"Mao esq.  {d.get('left_gesture', 'AUSENTE')}  {d.get('left_score', 0):.2f}",
        f"Mao dir.  {d.get('right_gesture', 'AUSENTE')}  {d.get('right_score', 0):.2f}",
        f"Score min {HAND_GESTURE_MIN_SCORE:.2f}",
        f"Coracao   {heart}",
        f"Indicadores {d.get('heart_index_contact', 99):.2f} <= {HAND_HEART_CONTACT_RATIO:.2f}",
        f"Polegares   {d.get('heart_thumb_contact', 99):.2f} <= {HAND_HEART_CONTACT_RATIO:.2f}",
        f"Gap vertical {d.get('heart_vertical_gap', 0):.2f} >= {HAND_HEART_MIN_VERTICAL_GAP_RATIO:.2f}",
    ]


def draw_hud(
    frame: Any,
    mode: str,
    state: Estado,
    fps: float,
    game_enabled: bool,
    calibrated: bool,
    calibration_message: str,
    classifier: Any,
    display_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Monta um dashboard em tela cheia e retorna a imagem final para cv2.imshow."""
    src_h, src_w = frame.shape[:2]
    if display_size is None:
        screen_w, screen_h = src_w, src_h
    else:
        screen_w = max(1024, int(display_size[0]))
        screen_h = max(640, int(display_size[1]))

    canvas = np.full((screen_h, screen_w, 3), BG, dtype=np.uint8)

    margin = max(16, int(screen_w * 0.012))
    top_h = max(76, int(screen_h * 0.075))
    bottom_h = max(52, int(screen_h * 0.055))
    sidebar_w = int(screen_w * 0.235)
    sidebar_w = max(HUD_SIDEBAR_MIN_WIDTH, min(HUD_SIDEBAR_MAX_WIDTH, sidebar_w))

    # Header
    _shadow_text(canvas, "SUBWAY VISION CONTROLLER", (margin, int(top_h * 0.62)), 0.82, TEXT, 2)

    mode_x = max(360, int(screen_w * 0.28))
    _rounded_rect(canvas, (mode_x, 20), (mode_x + 155, top_h - 17), PANEL_2, 14)
    _shadow_text(canvas, f"MODO  {mode}", (mode_x + 16, top_h // 2 + 7), 0.52, CYAN, 1)

    state_color = _state_color(state)
    state_x = mode_x + 170
    _rounded_rect(canvas, (state_x, 20), (state_x + 215, top_h - 17), state_color, 14)
    _shadow_text(canvas, state.value, (state_x + 18, top_h // 2 + 8), 0.62, (20, 22, 26), 2)

    fps_text = f"{fps:4.1f} FPS"
    active_text = "CONTROLE ATIVO" if game_enabled else "CONTROLE PAUSADO"
    active_color = ACCENT if game_enabled else RED
    right_header_x = screen_w - margin - 305
    _shadow_text(canvas, fps_text, (right_header_x, top_h // 2 + 7), 0.55, MUTED, 1)
    cv2.circle(canvas, (right_header_x + 130, top_h // 2), 7, active_color, -1, cv2.LINE_AA)
    _shadow_text(canvas, active_text, (right_header_x + 145, top_h // 2 + 7), 0.48, TEXT, 1)

    content_top = top_h + 4
    content_bottom = screen_h - bottom_h - margin
    sidebar_x = screen_w - margin - sidebar_w
    camera_x1 = margin
    camera_y1 = content_top
    camera_x2 = sidebar_x - margin
    camera_y2 = content_bottom

    # Camera card
    _rounded_rect(canvas, (camera_x1, camera_y1), (camera_x2, camera_y2), PANEL, 20)
    inner_pad = 10
    avail_w = camera_x2 - camera_x1 - inner_pad * 2
    avail_h = camera_y2 - camera_y1 - inner_pad * 2
    fitted = _fit_image(frame, avail_w, avail_h)
    fh, fw = fitted.shape[:2]
    fx = camera_x1 + inner_pad + (avail_w - fw) // 2
    fy = camera_y1 + inner_pad + (avail_h - fh) // 2
    canvas[fy:fy + fh, fx:fx + fw] = fitted
    cv2.rectangle(canvas, (fx, fy), (fx + fw, fy + fh), BORDER, 1, cv2.LINE_AA)

    # Badge dentro da camera.
    badge = "CALIBRADO" if calibrated else "CALIBRANDO"
    badge_color = ACCENT if calibrated else YELLOW
    _rounded_rect(canvas, (fx + 16, fy + 16), (fx + 150, fy + 54), PANEL, 12)
    cv2.circle(canvas, (fx + 34, fy + 35), 6, badge_color, -1, cv2.LINE_AA)
    _shadow_text(canvas, badge, (fx + 48, fy + 41), 0.43, TEXT, 1)

    if state == Estado.SEM_POSE:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (fx, fy), (fx + fw, fy + fh), (28, 28, 95), -1)
        cv2.addWeighted(overlay, 0.34, canvas, 0.66, 0, canvas)
        text = "SEM_POSE"
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3)[0]
        _shadow_text(canvas, text, (fx + (fw - size[0]) // 2, fy + fh // 2), 1.6, RED, 3)

    # Sidebar
    side_top = content_top
    gap = 12
    status_h = 110
    help_h = 190 if mode in {"PEITORAL", "MAOS"} else 160
    debug_y = side_top + status_h + gap + help_h + gap
    debug_h = max(180, content_bottom - debug_y)

    # Status card
    _rounded_rect(canvas, (sidebar_x, side_top), (sidebar_x + sidebar_w, side_top + status_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, side_top + 28, "ESTADO ATUAL")
    _shadow_text(canvas, state.value, (sidebar_x + 18, side_top + 72), 0.82, state_color, 2)
    subtitle = "F5 enviado ao jogo" if state == Estado.REINICIAR else calibration_message
    _shadow_text(canvas, subtitle[:45], (sidebar_x + 18, side_top + 98), 0.40, MUTED, 1)

    # Gestos card
    help_y = side_top + status_h + gap
    _rounded_rect(canvas, (sidebar_x, help_y), (sidebar_x + sidebar_w, help_y + help_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, help_y + 28, "COMANDOS DO MODO")
    _draw_lines(canvas, _mode_help(mode), sidebar_x + 18, help_y + 58, sidebar_w - 36, 28, 0.48)

    # Debug card
    _rounded_rect(canvas, (sidebar_x, debug_y), (sidebar_x + sidebar_w, debug_y + debug_h), PANEL, 18)
    _draw_card_title(canvas, sidebar_x + 18, debug_y + 28, "DEBUG / AJUSTE FINO")
    _draw_lines(canvas, _debug_lines(mode, classifier), sidebar_x + 18, debug_y + 58,
                sidebar_w - 36, 25, 0.45)

    # Footer
    footer_y = screen_h - bottom_h + 5
    _shadow_text(canvas, "F8", (margin, footer_y + 24), 0.52, CYAN, 2)
    f8_text = "reiniciar gestos" if mode == "MAOS" else "recalibrar"
    _shadow_text(canvas, f8_text, (margin + 42, footer_y + 24), 0.46, MUTED, 1)
    _shadow_text(canvas, "F10", (margin + 190, footer_y + 24), 0.52, CYAN, 2)
    _shadow_text(canvas, "sair", (margin + 244, footer_y + 24), 0.46, MUTED, 1)
    _shadow_text(canvas, "ESC", (margin + 330, footer_y + 24), 0.52, CYAN, 2)
    _shadow_text(canvas, "sair da interface", (margin + 382, footer_y + 24), 0.46, MUTED, 1)

    return canvas
```

## `vision/pose_detector.py`

```python
"""Wrapper do MediaPipe Pose Landmarker."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from config import (
    MIN_DETECTION_CONFIDENCE,
    MIN_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)


class PoseDetector:
    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo Pose Landmarker nao encontrado: {model_path}. "
                "Baixe pose_landmarker_lite.task e coloque em models/."
            )

        model_bytes = model_path.read_bytes()
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            output_segmentation_masks=False,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, frame_bgr: Any, timestamp_ms: int) -> list[Any] | None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.pose_landmarks:
            return None
        return result.pose_landmarks[0]

    def close(self) -> None:
        self._landmarker.close()
```

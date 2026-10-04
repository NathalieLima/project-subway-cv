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

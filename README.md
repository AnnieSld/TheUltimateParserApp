# The Ultimate Parser App

Analizador de gramáticas y cadenas con 6 métodos de parsing — proyecto para el
**Concurso de Desarrollo · CS3402 Compiladores 2026-1**.

## Qué incluye

**Top-Down**
- Descenso recursivo (backtracking, con traza de llamadas y retrocesos)
- LL(1) predictivo (tabla, simulación paso a paso)

**Bottom-Up**
- LR(0), SLR(1), LALR(1) y LR(1): construcción del autómata de ítems,
  tablas ACTION/GOTO, detección y explicación de conflictos, simulación
  paso a paso.

**Extras**
- Árbol de derivación / AST para cada análisis exitoso (Graphviz).
- Visualización del autómata LR (Graphviz), renderizado 100% en el navegador
  (sin necesidad de instalar Graphviz en el servidor).
- Asistente IA local (heurísticas propias, sin depender de una API externa):
  detecta recursión izquierda y prefijos comunes, explica en español los
  conflictos LL(1)/LR, explica errores de sintaxis, y compara los 5 métodos
  sobre la misma gramática y cadena.
- Transformaciones automáticas: eliminar recursión izquierda y factorizar
  por la izquierda, con un botón para aplicarlas directamente a la gramática.
- Teclado virtual con símbolos formales (→, ε, •, |, $).
- Historial de análisis de la sesión.
- Exportación de reportes a PDF (gramática, tablas, resultado).
- Gramáticas de ejemplo precargadas (incluye casos con recursión izquierda,
  conflictos shift/reduce tipo "dangling else", y un caso no-DCFL para
  ilustrar los límites de LR(1)).

## Cómo correr localmente

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre `http://localhost:8501`.

### Pruebas rápidas del motor (sin UI)

```bash
python tests/smoke_test.py
```

Ejercita los 6 parsers sobre todas las gramáticas de ejemplo y valida las
transformaciones de gramática (elimina recursión izquierda, factoriza).

## Despliegue en la nube (URL pública gratuita)

Recomendado: **Streamlit Community Cloud**.

1. Sube este proyecto a un repositorio de GitHub.
2. Entra a https://share.streamlit.io, conecta tu cuenta de GitHub.
3. Crea una nueva app apuntando a `app.py` en la rama principal.
4. Streamlit instalará `requirements.txt` automáticamente y te dará una URL
   pública (`https://<tu-app>.streamlit.app`).

No se necesita instalar el binario de Graphviz en el servidor: los
diagramas se generan como texto DOT y se renderizan en el navegador con el
componente `st.graphviz_chart`.

Como PWA: Streamlit sirve la app como una página web estándar; puedes
"instalarla" desde el navegador (Chrome/Edge → "Instalar aplicación") una
vez desplegada en una URL HTTPS pública.

## Estructura del proyecto

```
app.py                    Interfaz Streamlit (UI, pestañas, teclado virtual)
parsers/
  grammar.py               Gramática: parseo, FIRST/FOLLOW, transformaciones
  recursive_descent.py     Descenso recursivo con backtracking
  ll1.py                   Tabla LL(1) y simulación
  lr_items.py               Ítems LR, closure/goto, colecciones canónicas
  lr_tables.py              Tablas ACTION/GOTO (LR0/SLR1/LALR1/LR1) + simulación
  examples.py               Gramáticas de ejemplo
ai/
  explainer.py              Heurísticas: explicaciones y sugerencias
visualization/
  graphviz_utils.py         Generación de DOT (árboles y autómatas)
utils/
  export_pdf.py             Exportación de reportes PDF
  history.py                Historial de análisis
tests/
  smoke_test.py              Prueba de extremo a extremo del motor
```

## Notas de diseño

- La tabla LL(1) y las tablas ACTION/GOTO se calculan siempre (no solo al
  analizar una cadena), para que los conflictos se vean de inmediato.
- El descenso recursivo rechaza de entrada las gramáticas con recursión
  izquierda directa (con una explicación), en vez de colgarse en un ciclo
  infinito; además hay un límite de pasos como red de seguridad para
  recursión izquierda indirecta.
- LALR(1) se construye fusionando estados de la colección canónica LR(1)
  que comparten el mismo núcleo — el método estándar más simple de explicar
  en una demo, produce las mismas tablas que la construcción por
  propagación de lookaheads para gramáticas de este tamaño.

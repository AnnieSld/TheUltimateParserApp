# The Ultimate Parser App

Proyecto para el **Concurso de Desarrollo · CS3402 Compiladores 2026-1**.
Analiza gramaticas y cadenas de entrada con 6 metodos de parsing distintos
(descenso recursivo, LL(1), LR(0), SLR(1), LALR(1) y LR(1)), mostrando las
tablas, el proceso paso a paso y si la cadena se acepta o no.

## Que incluye

**Top-Down**
- Descenso recursivo (con backtracking, muestra la traza de llamadas y
  retrocesos)
- LL(1) predictivo (tabla de FIRST/FOLLOW, tabla de analisis, simulacion
  paso a paso)

**Bottom-Up**
- LR(0), SLR(1), LALR(1) y LR(1): construccion del automata de items,
  tablas ACTION/GOTO, deteccion y explicacion de conflictos, simulacion
  paso a paso.

**Extras**
- Arbol de derivacion / AST para cada analisis que se acepta (con Graphviz).
- Visualizacion del automata LR, tambien con Graphviz, renderizado en el
  navegador (no hace falta instalar nada en el servidor).
- Asistente IA con heuristicas propias (no llama a ningun modelo externo,
  son reglas locales): detecta recursion izquierda y prefijos comunes,
  explica los conflictos LL(1)/LR en español, explica errores de sintaxis,
  y compara los 5 metodos formales sobre la misma gramatica y cadena.
- Botones para eliminar recursion izquierda y factorizar por la izquierda
  automaticamente.
- Teclado virtual con los simbolos que cuesta escribir (→, ε, •, |, $).
- Historial de los analisis de la sesion.
- Exportar el reporte a PDF (gramatica, tablas, resultado).
- Gramaticas de ejemplo precargadas, incluyendo casos con recursion
  izquierda, un conflicto shift/reduce clasico (dangling-else), y un caso
  que ni siquiera es LR(1) para mostrar los limites de estos metodos.

## Como correrlo

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Se abre en `http://localhost:8501`.

### Probar que el motor funciona bien (sin abrir la interfaz)

```bash
python tests/smoke_test.py
```

Corre los 6 parsers sobre todas las gramaticas de ejemplo y valida las
transformaciones de gramatica (eliminar recursion izquierda, factorizar).
El script fue creciendo cada vez que aparecia algun caso raro que no
funcionaba bien, asi queda como red de seguridad para que no se rompa
de nuevo mas adelante.

## Despliegue (URL publica gratis)

Se uso **Streamlit Community Cloud**: es gratis y no requiere instalar
nada del lado del servidor (ni siquiera Graphviz, porque los dibujos se
generan como texto DOT y el navegador los renderiza solo, con
`st.graphviz_chart`).

1. Subir el proyecto a un repo de GitHub.
2. Entrar a https://share.streamlit.io y conectar la cuenta de GitHub.
3. Crear una app nueva apuntando a `app.py` en la rama `main`.
4. Streamlit instala el `requirements.txt` y da una URL publica
   (`https://<nombre-app>.streamlit.app`).

Como PWA: al ser una pagina web normal servida por HTTPS, se puede
"instalar" desde el navegador (Chrome/Edge → Instalar aplicacion) una vez
desplegada.

Link de la applicacion deployada: https://theultimateparserapp.streamlit.app/

## Estructura del proyecto

```
app.py                    Interfaz de Streamlit (pestañas, teclado virtual, todo lo visual)
parsers/
  grammar.py               La gramatica: parseo del texto, FIRST/FOLLOW, transformaciones
  recursive_descent.py     Descenso recursivo con backtracking
  ll1.py                   Tabla LL(1) y simulacion paso a paso
  lr_items.py              Items LR, closure/goto, colecciones canonicas
  lr_tables.py             Tablas ACTION/GOTO para LR0/SLR1/LALR1/LR1 + simulacion
  examples.py              Gramaticas de ejemplo precargadas
ai/
  explainer.py             Heuristicas: explicaciones y sugerencias en español
visualization/
  graphviz_utils.py        Arma el texto DOT para los arboles y los automatas
utils/
  export_pdf.py            Exportar el reporte a PDF
  history.py                Historial de los analisis
tests/
  smoke_test.py             Prueba de punta a punta del motor
```

## Notas / cosas a tener en cuenta

- El descenso recursivo revisa si hay recursion izquierda directa ANTES de
  intentar parsear, y avisa en vez de colgarse: si no se hiciera esa
  revision, una gramatica como `E -> E + T` haria que la funcion se llame a
  si misma sin consumir nada de la entrada, osea un ciclo infinito de
  verdad (Python termina tirando `RecursionError`).
- LALR(1) se construye armando primero el automata LR(1) completo y
  despues fusionando los estados que comparten el mismo "core" (mismas
  producciones y puntos, distinto lookahead). Da las mismas tablas que
  construirlo de forma directa por propagacion de lookaheads, pero es
  bastante mas facil de programar y de explicar.
- El tokenizador de la gramatica soporta simbolos pegados sin espacio del
  estilo `S -> AB`, `A -> aA` (muy comun en gramaticas de una sola letra):
  reconoce los no terminales ya declarados dentro de una palabra pegada y
  los separa, sin romper terminales de varias letras como `id` o `then`. Sin embargo para colocar A + B, el + debe ir separado.

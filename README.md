# The Ultimate Parser App

Proyecto para el **Concurso de Desarrollo · CS3402 Compiladores 2026-1**.
Link de la app deployada: https://theultimateparserapp.streamlit.app/
## 1. Objetivo y motivacion

La app analiza gramaticas y cadenas de entrada con 6 metodos de parsing
distintos: descenso recursivo, LL(1), LR(0), SLR(1), LALR(1) y LR(1). La
idea no era solo "que funcione", sino que se pueda ver el proceso interno
de cada metodo (tablas, automata, paso a paso) para que sirva como
herramienta de estudio y no solo como validador de cadenas. Por eso cada
pestaña muestra la construccion completa (FIRST/FOLLOW, tabla LL(1), items
LR, ACTION/GOTO) antes de siquiera analizar una cadena, y hay un asistente
que explica en español por que algo fallo o por que una gramatica tiene
conflictos.

## 2. Demostracion funcional (con gramaticas de ejemplo)

La app trae varias gramaticas precargadas (menu "Cargar gramatica de
ejemplo" en la barra lateral) pensadas para mostrar comportamientos
distintos:

- **Expresiones aritmeticas con recursion izquierda** (`E -> E + T | T`, ...)
  con la cadena `id + id * id`. Sirve para mostrar que LR(0) tiene
  conflictos, SLR(1)/LALR(1)/LR(1) no, y que el descenso recursivo / LL(1)
  rechazan la gramatica tal cual (por la recursion izquierda) hasta que se
  usa el boton "Eliminar recursion izquierda" del Asistente IA.
- **La misma gramatica sin recursion izquierda**, ya lista para LL(1), con
  la misma cadena -- para comparar antes/despues de la transformacion.
- **If-then-else** (`S -> if E then S | if E then S else S | other`) con
  `if id then if id then other else other`: el ejemplo clasico de conflicto
  shift/reduce (dangling-else), presente en los 4 metodos LR.
- **Simbolos de una sola letra sin espacios** (`S -> AB`, `A -> aA | ε`,
  `B -> b`): prueba que el tokenizador separa bien los simbolos aunque se
  escriban pegados, sin romper terminales de varias letras como `id`.
- **Palindromos con a/b** (`S -> a S a | b S b | a | b | ε`): un caso que
  NI SIQUIERA LR(1) resuelve sin conflictos, para mostrar que hay lenguajes
  libres de contexto que no son manejables por ningun parser LR(k) (no son
  DCFL), no es un bug del programa.

Con cualquiera de estos: se elige la pestaña del metodo, se revisan las
tablas que ya estan calculadas, y se aprieta "Analizar cadena" para ver la
simulacion paso a paso y el arbol de derivacion si se acepta. La pestaña
"Comparar" corre los 5 metodos formales (LL1 + los 4 LR) sobre la misma
gramatica y cadena a la vez, para ver de un vistazo cuales la aceptan y
cuantos conflictos tiene cada uno.

## 3. Arquitectura y algoritmos implementados

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

La logica esta separada de la interfaz a proposito: `app.py` no calcula
nada, solo llama a las funciones de `parsers/` y muestra el resultado. Asi
`parsers/` se puede probar solo (`tests/smoke_test.py`) sin tener que abrir
la app cada vez.

El flujo general es: texto de la gramatica -> `Grammar.parse()` la
convierte en producciones -> segun el metodo elegido, se calculan
FIRST/FOLLOW (top-down) o se construye el automata de items LR
(bottom-up) -> se arma la tabla correspondiente -> se simula la cadena de
entrada contra esa tabla, paso a paso, guardando cada paso para mostrarlo
en la UI.

Los algoritmos en si son los del curso: closure/goto para armar la
coleccion canonica de items LR(0)/LR(1), FIRST/FOLLOW por punto fijo,
eliminacion de recursion izquierda y factorizacion por la izquierda segun
el algoritmo estandar. La unica decision de diseño no tan obvia es como se
construye LALR(1): en vez de la construccion "directa" con propagacion de
lookaheads (que es mas eficiente pero mas dificil de programar bien), se
arma el automata LR(1) completo y despues se fusionan los estados que
tienen el mismo nucleo (mismas producciones-con-punto, distinto
lookahead). Da las mismas tablas para gramaticas de este tamaño, y es
mucho mas facil de verificar que este bien.

## 4. Uso de IA durante el desarrollo

Este proyecto se construyo con Claude (Claude Code) como copiloto durante
todo el desarrollo, tal como pide la seccion 3 del enunciado. En concreto
se uso para:

- Generar la primera version de cada parser (descenso recursivo, LL(1), y
  el motor generico de items LR que comparten LR(0)/SLR(1)/LALR(1)/LR(1)).
- Depuracion: por ejemplo, se encontro con pruebas reales que el
  tokenizador de la gramatica interpretaba mal simbolos pegados sin
  espacio (`S -> AB` se leia como un solo simbolo "AB" en vez de "A" y
  "B"), lo cual daba FIRST/FOLLOW incorrectos sin ningun error visible. Se
  detecto probando la gramatica `S -> AB | A -> aA | B -> b` y comparando
  el resultado contra el calculo hecho a mano; con eso se corrigio el
  tokenizador para que reconozca los no terminales ya declarados dentro de
  una palabra pegada.
- Pruebas: `tests/smoke_test.py` corre los 6 parsers sobre todas las
  gramaticas de ejemplo y quedo como prueba de regresion (incluye el caso
  de arriba, para que ese bug no vuelva a aparecer sin darse cuenta).
- Diseño de interfaz: la estructura de pestañas en Streamlit, el "asistente
  IA" con heuristicas locales (sin llamar a ningun modelo externo -- son
  reglas escritas para este proyecto, en `ai/explainer.py`), y las
  visualizaciones con Graphviz.
- Documentacion: este README y los comentarios en el codigo.

Todo el codigo fue revisado y probado manualmente (no solo generado y
copiado): cada parser se corrio contra varias gramaticas y se comparo el
resultado contra lo que da el algoritmo a mano, y varias veces aparecieron
casos que no funcionaban bien a la primera (recursion izquierda colgando
el descenso recursivo, el bug de tokenizacion mencionado arriba, etc.) que
se fueron corrigiendo con ese proceso de prueba y error.

## 5. Visualizaciones y funcionalidades destacadas

- Arbol de derivacion / AST para cada analisis que se acepta, con Graphviz.
- Visualizacion del automata LR (estados e items), tambien con Graphviz,
  renderizado en el navegador sin instalar nada en el servidor.
- Tablas ACTION/GOTO y FIRST/FOLLOW dinamicas, recalculadas apenas cambia
  la gramatica.
- Asistente IA con heuristicas propias: detecta recursion izquierda y
  prefijos comunes, explica los conflictos LL(1)/LR en español (shift-
  reduce vs reduce-reduce, con sugerencia concreta segun el patron
  detectado), explica errores de sintaxis, y compara los 5 metodos
  formales sobre la misma gramatica y cadena.
- Botones para eliminar recursion izquierda y factorizar por la izquierda
  automaticamente, aplicables con un clic.
- Teclado virtual con los simbolos que cuesta escribir (→, ε, •, |, $).
- Historial de los analisis de la sesion, exportacion del reporte a PDF.

## 6. Despliegue y guia rapida de uso

**Como correrlo localmente:**

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Se abre en `http://localhost:8501`.

**Guia rapida:** en la barra lateral se escribe (o se carga un ejemplo de)
la gramatica, una regla por linea (`A -> alfa | beta`, usando ε para
vacio); se escribe la cadena a analizar (tokens separados por espacios); y
se elige la pestaña del metodo que se quiera usar. Cada pestaña ya muestra
las tablas construidas; el boton "Analizar cadena" corre la simulacion
paso a paso y muestra si se acepta o no, con el arbol de derivacion si
aplica.

**Probar que el motor funciona bien (sin abrir la interfaz):**

```bash
python tests/smoke_test.py
```

**Despliegue en la nube (URL publica gratis):** se uso **Streamlit
Community Cloud**, que es gratis y no requiere instalar nada del lado del
servidor (ni siquiera Graphviz, porque los dibujos se generan como texto
DOT y el navegador los renderiza solo, con `st.graphviz_chart`).

1. Subir el proyecto a un repo de GitHub (ya esta: `AnnieSld/TheUltimateParserApp`).
2. Entrar a https://share.streamlit.io y conectar la cuenta de GitHub.
3. Crear una app nueva apuntando a `app.py` en la rama `main`.
4. Streamlit instala el `requirements.txt` y da una URL publica
   (`https://<nombre-app>.streamlit.app`).

Como PWA: al ser una pagina web normal servida por HTTPS, se puede
"instalar" desde el navegador (Chrome/Edge → Instalar aplicacion) una vez
desplegada.

## Notas tecnicas / cosas a tener en cuenta

- El descenso recursivo revisa si hay recursion izquierda directa ANTES de
  intentar parsear, y avisa en vez de colgarse: si no se hiciera esa
  revision, una gramatica como `E -> E + T` haria que la funcion se llame a
  si misma sin consumir nada de la entrada, osea un ciclo infinito de
  verdad (Python termina tirando `RecursionError`).
- El tokenizador de la gramatica soporta simbolos pegados sin espacio del
  estilo `S -> AB`, `A -> aA` (muy comun en gramaticas de una sola letra):
  reconoce los no terminales ya declarados dentro de una palabra pegada y
  los separa, sin romper terminales de varias letras como `id` o `then`.
  Para simbolos terminales sueltos (como `+`, `*`) que no van pegados a
  ningun no terminal, si conviene escribirlos separados por espacio.

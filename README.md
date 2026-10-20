# Justificante de asistencia (clases en línea)

Cada estudiante abre un enlace, rellena sus datos, firma con el dedo en su propio
dispositivo y descarga un PDF que envía al docente. Sin servidor, sin base de datos y
sin cuentas de terceros: dos ficheros HTML y un verificador en Python.

- Página del alumno: `index.html`
- Generador de enlaces por sesión (para el docente): `generador.html`
- Verificador de un PDF recibido: `verificar_pdf.py`

## Uso

1. Abre `generador.html`, rellena acción formativa, fecha y modalidad ("En línea") y
   copia el enlace que produce. Ese enlace ya lleva la sesión dentro.
2. Pégalo en el aula virtual, en el correo o en el chat de la clase.
3. Cada estudiante firma y descarga `Justificante-AAAA-MM-DD-APELLIDOS.pdf`.
4. Te lo envía. Opcionalmente, que lo suba a una tarea de "entrega de archivo": así ves
   quién ha entregado sin contar mensajes.

## Qué lleva el PDF

A4 con la acción formativa, la fecha de la sesión, la modalidad, el lugar, el docente,
apellidos y nombre, DNI/NIE, la firma incrustada y dos huellas SHA-256: la de la imagen y
la del registro.

El documento **no indica cuándo se firmó**: si un alumno firma días después, el
justificante sigue siendo el de la sesión y no delata la fecha de la firma (el PDF tampoco
lleva `/CreationDate` en sus metadatos).

Comprobación de un justificante recibido:

```sh
python3 verificar_pdf.py justificante.pdf
```

Extrae el texto y la imagen del propio PDF, recalcula las huellas y las compara con las
impresas. Si alguien ha editado un dato o la firma, devuelve "EL DOCUMENTO NO CUADRA"
y código de salida 1.

## Identificación del asistente

El campo se llama **DNI / NIE / Pasaporte** y **no se valida el formato español** como
condición para firmar: el alumnado puede ser internacional y un formato cerrado deja fuera
a quien trae un pasaporte o un documento de otro país. La exactitud del número es
responsabilidad de quien firma; el centro lo coteja después.

Lo que sí se comprueba, por robustez y no por corrección:

- **longitud** entre 4 y 20 caracteres, con letras, cifras y `. - /` (nada de símbolos ni
  de cadenas vacías que no sirven como registro);
- se eliminan caracteres de control, marcas de dirección (bidi), espacios de ancho cero y
  se colapsan los espacios repetidos;
- límites de longitud en nombre (60) y apellidos (90);
- **aviso no bloqueante** si tiene pinta de DNI o NIE y la letra no cuadra: "Parece un DNI:
  la letra no cuadra con el número (sería 12345678Z). Revísalo; puedes continuar
  igualmente." — se caza el error de tecleo sin cerrar la puerta a nadie;
- se rechaza un nombre con caracteres que el PDF no puede escribir (fuera de Windows-1252,
  p. ej. cirílico o chino) con un mensaje que pide alfabeto latino, porque el generador usa
  fuentes estándar y los convertiría en `?`.

## Pruebas

El harness necesita servidor local (los navegadores no dejan cargar iframes por `file://`
con las mismas garantías):

```sh
python3 -m http.server 8103            # en la raíz del proyecto
google-chrome --headless=new --no-sandbox --disable-gpu \
  --user-data-dir=/tmp/chk --virtual-time-budget=25000 \
  --dump-dom http://127.0.0.1:8103/pruebas/tests_justificante.html > /tmp/dom.html
# esperado: RESUMEN PASS=33 FAIL=0
```

## Límites conocidos

- Sin servidor no hay deduplicación: alguien puede firmar dos veces o poner un DNI ajeno.
  El documento acredita "una declaración de asistencia firmada en este dispositivo a esta
  hora", no la identidad de quien firma.
- Si un estudiante no envía el PDF, no queda registro.
- iOS a veces abre el PDF en el visor en vez de guardarlo; el recibo en pantalla ofrece
  un botón de reserva "Imprimir / guardar como PDF".

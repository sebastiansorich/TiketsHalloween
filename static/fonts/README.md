# Fuentes para el proyecto

## Instalación de fuente

Para que el texto se vea correctamente en el servidor (Vercel/Linux), necesitas agregar una fuente TrueType (.ttf) en esta carpeta.

### Opción 1: Usar una fuente de Google Fonts (Recomendado)

1. Ve a [Google Fonts](https://fonts.google.com/)
2. Descarga la fuente **Roboto** o **Open Sans** (son gratuitas y se ven bien)
3. Descomprime el archivo ZIP
4. Copia el archivo `Roboto-Bold.ttf` o `Roboto-Regular.ttf` a esta carpeta
5. Renombra el archivo a `Arial.ttf`

### Opción 2: Usar DejaVu Sans (Alternativa libre)

1. Ve a [DejaVu Fonts](https://dejavu-fonts.github.io/)
2. Descarga DejaVu Sans
3. Copia `DejaVuSans-Bold.ttf` a esta carpeta
4. Renombra el archivo a `Arial.ttf`

### Opción 3: Copiar desde Windows

Si estás en Windows, puedes copiar Arial desde:
```
C:\Windows\Fonts\arial.ttf
```

Y pegarlo en esta carpeta.

## Verificación

Después de agregar la fuente, el sistema debería poder cargarla automáticamente.
Si ves en los logs del servidor: "✓ Fuente cargada: ...", significa que funcionó correctamente.


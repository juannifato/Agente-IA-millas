# Fase 5 — Interfaz en Visual Basic (guía de integración)

Esta guía deja listo todo lo que la app de escritorio necesita para hablar con
el backend, que ya está terminado y probado (Fase 4). No incluye la GUI armada
porque en esta máquina no se puede compilar ni ver (falta el entorno, ver abajo)
y el diseño del formulario es una decisión de Juan.

## Destrabar el entorno primero

**No hay .NET SDK ni Visual Studio en la máquina.** No hace falta Visual Studio:
con el SDK y su CLI `dotnet` se crea y compila una app WinForms en VB.NET. En
winget está disponible (hasta .NET 10). Recomendado el LTS más nuevo:

```powershell
winget install Microsoft.DotNet.SDK.10        # o .SDK.8, tambien LTS
# cerrar y reabrir la terminal para que 'dotnet' entre al PATH
dotnet --version                               # confirmar que quedo instalado
```

Crear el proyecto (WinForms, lenguaje VB):

```powershell
dotnet new winforms -lang VB -o MillasApp
cd MillasApp
dotnet run                                     # compila y abre la ventana
```

> Decisión pendiente de Juan: confirmar que vamos con **WinForms** (lo más
> simple y lo que pide el plan) y con qué versión del SDK. Recién ahí se arma
> el formulario.

## Qué endpoints consume la app

El backend corre local en `http://127.0.0.1:3000` (en producción será la URL de
Render, Fase 6). Tres endpoints:

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/salud` | Chequear que el backend está vivo al arrancar la app. |
| GET | `/aerolineas` | Llenar el combo de aerolíneas: `[{clave, nombre}]`. |
| POST | `/buscar` | La búsqueda. Manda JSON, recibe la recomendación. |

## El request de `/buscar`

```json
{"origen":"AEP", "destino":"BRC", "fecha":"15/09/2026",
 "fecha_vuelta":"22/09/2026", "adultos":1, "aerolinea":"aerolineas_arg"}
```

- **La fecha va en `DD/MM/AAAA`** (también acepta ISO, pero VB manda ese formato).
- `fecha_vuelta`, `adultos` (default 1) y `aerolinea` (default la primera) son
  opcionales. Sin `fecha_vuelta` se busca solo ida.

## La respuesta de `/buscar`

Caso normal (probado, ida y vuelta):

```json
{
  "ok": true,
  "consulta": { "origen":"AEP", "destino":"BRC", "fecha":"2026-09-15",
                "fecha_vuelta":"2026-09-22", "adultos":1, "aerolinea":"aerolineas_arg" },
  "mejor": {
    "millas": 53000,
    "impuestos": 128044,
    "tramos": [
      { "tramo":"ida", "numeros":["AR1200","AR1502"], "origen":"AEP", "destino":"BRC",
        "sale":"2026-09-15T06:00", "llega":"2026-09-15T10:20", "escalas":1,
        "duracion_min":260, "tarifa":"Economy Promo", "millas":25000,
        "impuestos":64022, "asientos":9 },
      { "tramo":"vuelta", "numeros":["AR1687"], "origen":"BRC", "destino":"AEP",
        "sale":"2026-09-22T21:00", "llega":"2026-09-22T23:25", "escalas":0,
        "duracion_min":145, "tarifa":"Economy Promo", "millas":28000,
        "impuestos":64022, "asientos":6 }
    ]
  },
  "analisis": "Texto corto en español explicando por qué es la más conveniente.",
  "eleccion_por_ia": true,
  "opciones_evaluadas": 4
}
```

Tres formas que la app tiene que contemplar:

1. **Éxito con resultado:** `ok:true` y `mejor` con datos. Mostrar `mejor.millas`,
   `mejor.impuestos`, el texto de `analisis` y cada `mejor.tramos[]` en una grilla.
2. **Éxito sin vuelos:** `ok:true` pero `mejor:null` y un `mensaje`. Mostrar el
   mensaje ("No se encontraron vuelos en millas para esas fechas.").
3. **Error:** `ok:false` con `motivo` (código corto) y `error` (texto para el
   usuario). Mostrar el `error`; el `motivo` sirve para reaccionar distinto:
   - `datos_invalidos` (HTTP 400): algo que cargó el usuario está mal.
   - `token_vencido` / `falta_token` (503): problema de configuración del backend.
   - `token_no_obtenido`, `formato_desconocido`, `ia_*` (502): falló un servicio del que dependemos.

**Todas** las respuestas son JSON, incluso los errores 404 y 500, así que se
puede deserializar siempre sin miedo a que llegue HTML.

## Cliente de referencia en VB.NET

> ⚠️ **Sin compilar en esta máquina** (no hay .NET SDK). Es una plantilla para
> ajustar al integrarla, no código verificado. Usa `HttpClient` y
> `System.Text.Json`, ambos incluidos en .NET, sin paquetes extra.

```vb
Imports System.Net.Http
Imports System.Text
Imports System.Text.Json

' --- Clases que mapean el JSON de /buscar ---
Public Class Respuesta
    Public Property ok As Boolean
    Public Property motivo As String
    Public Property [error] As String      ' 'error' es palabra reservada: entre corchetes
    Public Property mensaje As String
    Public Property analisis As String
    Public Property eleccion_por_ia As Boolean
    Public Property opciones_evaluadas As Integer
    Public Property mejor As Mejor
End Class

Public Class Mejor
    Public Property millas As Integer
    Public Property impuestos As Integer
    Public Property tramos As List(Of Tramo)
End Class

Public Class Tramo
    Public Property tramo As String
    Public Property numeros As List(Of String)
    Public Property origen As String
    Public Property destino As String
    Public Property sale As String
    Public Property llega As String
    Public Property escalas As Integer
    Public Property duracion_min As Integer?
    Public Property tarifa As String
    Public Property millas As Integer
    Public Property impuestos As Integer
    Public Property asientos As Integer?
End Class

Public Class ClienteApi
    ' HttpClient se instancia UNA sola vez y se reutiliza (crear uno por
    ' request agota los sockets del sistema).
    Private Shared ReadOnly http As New HttpClient()
    Private Const BaseUrl As String = "http://127.0.0.1:3000"   ' Fase 6: URL de Render

    Public Shared Async Function BuscarAsync(consulta As Object) As Task(Of Respuesta)
        Dim json As String = JsonSerializer.Serialize(consulta)
        Dim cuerpo As New StringContent(json, Encoding.UTF8, "application/json")
        Dim resp As HttpResponseMessage = Await http.PostAsync(BaseUrl & "/buscar", cuerpo)
        Dim texto As String = Await resp.Content.ReadAsStringAsync()
        ' El backend manda JSON hasta en los errores, asi que se deserializa igual.
        Dim opts As New JsonSerializerOptions With {.PropertyNameCaseInsensitive = True}
        Return JsonSerializer.Deserialize(Of Respuesta)(texto, opts)
    End Function
End Class
```

Uso desde el botón "Buscar":

```vb
Private Async Sub btnBuscar_Click(sender As Object, e As EventArgs) Handles btnBuscar.Click
    ' fecha_vuelta va como Nothing si el usuario no la cargo (busqueda solo ida).
    Dim consulta = New With {
        .origen = txtOrigen.Text.Trim().ToUpper(),
        .destino = txtDestino.Text.Trim().ToUpper(),
        .fecha = txtFecha.Text.Trim(),
        .fecha_vuelta = If(String.IsNullOrWhiteSpace(txtVuelta.Text), Nothing, txtVuelta.Text.Trim())
    }

    Try
        Dim r = Await ClienteApi.BuscarAsync(consulta)

        If Not r.ok Then
            MessageBox.Show(r.error, "No se pudo buscar (" & r.motivo & ")")
            Return
        End If
        If r.mejor Is Nothing Then
            MessageBox.Show(r.mensaje, "Sin resultados")
            Return
        End If

        lblResumen.Text = $"{r.mejor.millas} millas + {r.mejor.impuestos} de impuestos"
        lblAnalisis.Text = r.analisis
        dgvTramos.DataSource = r.mejor.tramos   ' un DataGridView muestra los tramos
    Catch ex As Exception
        ' Timeout, backend apagado, sin internet: nunca dejar que explote la app.
        MessageBox.Show("No se pudo conectar con el backend: " & ex.Message, "Error de conexión")
    End Try
End Sub
```

## Probar la integración sin la GUI

Antes de armar el formulario conviene ver el backend respondiendo. Levantarlo:

```powershell
.\.venv\Scripts\python.exe app.py
```

Y desde otra terminal, pegarle (necesita un `AEROLINEAS_TOKEN` vigente para una
búsqueda real; `/salud` y `/aerolineas` no):

```powershell
curl http://127.0.0.1:3000/salud
curl http://127.0.0.1:3000/aerolineas
```

Imports System.Net.Http
Imports System.Text
Imports System.Text.Json
Imports System.Threading.Tasks

' Cliente HTTP y modelos para hablar con el backend Python.
' El contrato esta documentado en docs/fase5_visual_basic.md. Los nombres de las
' propiedades coinciden con las claves del JSON (matching case-insensitive), asi
' que System.Text.Json las completa solo.

Public Class Respuesta
    Public Property ok As Boolean
    Public Property motivo As String
    Public Property [error] As String        ' 'error' es palabra reservada: entre corchetes
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

    ' --- Propiedades calculadas solo para mostrar en la grilla (no vienen del JSON) ---
    Public ReadOnly Property VuelosTexto As String
        Get
            Return If(numeros Is Nothing, "", String.Join(" + ", numeros))
        End Get
    End Property

    Public ReadOnly Property RutaTexto As String
        Get
            Return $"{origen} -> {destino}"
        End Get
    End Property

    Public ReadOnly Property SaleTexto As String
        Get
            Return FormatearFechaHora(sale)
        End Get
    End Property

    Public ReadOnly Property LlegaTexto As String
        Get
            Return FormatearFechaHora(llega)
        End Get
    End Property

    Public ReadOnly Property EscalasTexto As String
        Get
            If escalas <= 0 Then Return "Directo"
            Return escalas.ToString() & " escala" & If(escalas > 1, "s", "")
        End Get
    End Property

    Public ReadOnly Property DuracionTexto As String
        Get
            If Not duracion_min.HasValue Then Return ""
            Return $"{duracion_min.Value \ 60}h {duracion_min.Value Mod 60:00}m"
        End Get
    End Property

    Public ReadOnly Property MillasTexto As String
        Get
            Return millas.ToString("N0")
        End Get
    End Property

    Public ReadOnly Property ImpuestosTexto As String
        Get
            Return "$ " & impuestos.ToString("N0")
        End Get
    End Property

    ' Las horas vienen como "2026-09-15T08:10"; se muestran como "15/09 08:10".
    Private Shared Function FormatearFechaHora(iso As String) As String
        Dim d As DateTime
        If DateTime.TryParse(iso, d) Then Return d.ToString("dd/MM HH:mm")
        Return If(iso, "")
    End Function
End Class

Public Class RespuestaAerolineas
    Public Property ok As Boolean
    Public Property aerolineas As List(Of Aerolinea)
End Class

Public Class Aerolinea
    Public Property clave As String
    Public Property nombre As String
End Class

Public Class RespuestaAeropuertos
    Public Property ok As Boolean
    Public Property aeropuertos As List(Of Aeropuerto)
End Class

Public Class Aeropuerto
    Public Property iata As String
    Public Property ciudad As String
    Public Property pais As String
    Public Property nombre As String

    ' Lo que se ve en la lista desplegable, al estilo del sitio de Aerolineas:
    ' "Buenos Aires, Argentina (AEP)".
    Public ReadOnly Property Display As String
        Get
            Return $"{ciudad}, {pais} ({iata})"
        End Get
    End Property

    ' Texto sobre el que filtra el autocompletado: sirve escribir el codigo,
    ' la ciudad, el pais o el nombre del aeropuerto.
    Public ReadOnly Property Buscar As String
        Get
            Return $"{iata} {ciudad} {pais} {nombre}".ToUpper()
        End Get
    End Property
End Class

Public Class RespuestaChat
    Public Property ok As Boolean
    Public Property accion As String
    Public Property respuesta As String
    Public Property estado As EstadoChat
    Public Property mejor As Mejor
    Public Property eleccion_por_ia As Boolean
    Public Property opciones_evaluadas As Integer?
    Public Property motivo As String
End Class

' Lo que el chat sabe de la busqueda hasta ahora. Se guarda entre mensajes y se
' reenvia en cada uno, porque el backend no guarda sesion (memoria multi-turno).
Public Class EstadoChat
    Public Property origen As String
    Public Property destino As String
    Public Property fecha As String
    Public Property fecha_vuelta As String
    Public Property adultos As Integer?
End Class

' Un mensaje del chat, para las burbujas de la conversacion.
Public Class MensajeChat
    Public Property Texto As String
    Public Property EsUsuario As Boolean

    Public Sub New(texto As String, esUsuario As Boolean)
        Me.Texto = texto
        Me.EsUsuario = esUsuario
    End Sub
End Class

Public Class ClienteApi
    ' HttpClient se instancia UNA sola vez y se reutiliza: crear uno por request
    ' agota los sockets del sistema.
    Private Shared ReadOnly http As New HttpClient()

    ' Backend local. En la Fase 6 (Render) se reemplaza por la URL publica.
    Public Const BaseUrl As String = "http://127.0.0.1:3000"

    Private Shared ReadOnly opciones As New JsonSerializerOptions With {
        .PropertyNameCaseInsensitive = True
    }

    Public Shared Async Function BuscarAsync(consulta As Dictionary(Of String, Object)) As Task(Of Respuesta)
        Dim json As String = JsonSerializer.Serialize(consulta)
        Using cuerpo As New StringContent(json, Encoding.UTF8, "application/json")
            Dim resp As HttpResponseMessage = Await http.PostAsync(BaseUrl & "/buscar", cuerpo)
            Dim texto As String = Await resp.Content.ReadAsStringAsync()
            ' El backend manda JSON hasta en los errores, asi que se deserializa igual.
            Return JsonSerializer.Deserialize(Of Respuesta)(texto, opciones)
        End Using
    End Function

    Public Shared Async Function AerolineasAsync() As Task(Of List(Of Aerolinea))
        Dim texto As String = Await http.GetStringAsync(BaseUrl & "/aerolineas")
        Dim r As RespuestaAerolineas = JsonSerializer.Deserialize(Of RespuestaAerolineas)(texto, opciones)
        Return If(r?.aerolineas, New List(Of Aerolinea)())
    End Function

    Public Shared Async Function AeropuertosAsync() As Task(Of List(Of Aeropuerto))
        Dim texto As String = Await http.GetStringAsync(BaseUrl & "/aeropuertos")
        Dim r As RespuestaAeropuertos = JsonSerializer.Deserialize(Of RespuestaAeropuertos)(texto, opciones)
        Return If(r?.aeropuertos, New List(Of Aeropuerto)())
    End Function

    Public Shared Async Function ChatAsync(mensaje As String, estado As EstadoChat) As Task(Of RespuestaChat)
        Dim payload As New Dictionary(Of String, Object) From {{"mensaje", mensaje}}
        If estado IsNot Nothing Then payload("estado") = estado
        Dim json As String = JsonSerializer.Serialize(payload)
        Using cuerpo As New StringContent(json, Encoding.UTF8, "application/json")
            Dim resp As HttpResponseMessage = Await http.PostAsync(BaseUrl & "/chat", cuerpo)
            Dim texto As String = Await resp.Content.ReadAsStringAsync()
            Return JsonSerializer.Deserialize(Of RespuestaChat)(texto, opciones)
        End Using
    End Function
End Class

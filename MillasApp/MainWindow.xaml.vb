Imports System.Linq
Imports System.Threading.Tasks
Imports System.Windows.Controls.Primitives
Imports System.Windows.Input

' Ventana principal. Toma lo que carga el usuario, se lo manda al backend y
' muestra la recomendacion. La logica de red y los modelos estan en ClienteApi.vb.
Class MainWindow

    ' Lista completa de aeropuertos; se filtra sobre esta para el autocompletado.
    Private todosAeropuertos As New List(Of Aeropuerto)

    Public Sub New()
        InitializeComponent()
        ' Combo de adultos: 1 a 9 (lo que acepta la API).
        For i As Integer = 1 To 9
            cboAdultos.Items.Add(i)
        Next
        cboAdultos.SelectedIndex = 0
    End Sub

    ' Al abrirse la ventana se piden aerolineas y aeropuertos al backend.
    Private Async Sub Window_Loaded(sender As Object, e As RoutedEventArgs)
        Await CargarAerolineas()
        Await CargarAeropuertos()
    End Sub

    Private Async Function CargarAerolineas() As Task
        Try
            Dim lista As List(Of Aerolinea) = Await ClienteApi.AerolineasAsync()
            cboAerolinea.ItemsSource = lista
            If lista.Count > 0 Then cboAerolinea.SelectedIndex = 0
        Catch ex As Exception
            ' Si el backend no esta prendido no se rompe: se avisa y se puede reintentar.
            txtEstado.Text = "No se pudo conectar con el backend en " & ClienteApi.BaseUrl &
                             ". ¿Está corriendo? (" & ex.Message & ")"
        End Try
    End Function

    Private Async Function CargarAeropuertos() As Task
        Try
            todosAeropuertos = Await ClienteApi.AeropuertosAsync()
            cboOrigen.ItemsSource = todosAeropuertos
            cboDestino.ItemsSource = todosAeropuertos
        Catch ex As Exception
            ' Sin la lista igual se puede escribir el codigo IATA a mano.
        End Try
    End Function

    ' Autocompletado: a medida que se escribe, se filtra la lista por codigo,
    ' ciudad o nombre, y se abre el desplegable con las coincidencias.
    Private Sub Aeropuerto_KeyUp(sender As Object, e As KeyEventArgs)
        Dim cbo As ComboBox = TryCast(sender, ComboBox)
        If cbo Is Nothing Then Return
        ' Las teclas de navegacion y seleccion no disparan filtrado.
        If e.Key = Key.Down OrElse e.Key = Key.Up OrElse e.Key = Key.Enter OrElse
           e.Key = Key.Tab OrElse e.Key = Key.Escape Then Return

        Dim texto As String = If(cbo.Text, "")
        If texto.Trim() = "" Then
            cbo.ItemsSource = todosAeropuertos
            cbo.IsDropDownOpen = False
            Return
        End If

        Dim t As String = texto.ToUpper()
        Dim filtrados = todosAeropuertos.Where(Function(a) a.Buscar.Contains(t)).ToList()
        cbo.ItemsSource = filtrados
        cbo.IsDropDownOpen = filtrados.Count > 0

        ' Cambiar ItemsSource borra el texto tipeado: se restaura, con el cursor al final.
        cbo.Text = texto
        Dim tb As TextBox = TryCast(cbo.Template.FindName("PART_EditableTextBox", cbo), TextBox)
        If tb IsNot Nothing Then tb.CaretIndex = tb.Text.Length
    End Sub

    ' Devuelve el codigo IATA: el del aeropuerto elegido de la lista, o las
    ' primeras 3 letras de lo tipeado si el usuario escribio el codigo directo.
    Private Function ObtenerIata(cbo As ComboBox) As String
        Dim sel As Aeropuerto = TryCast(cbo.SelectedItem, Aeropuerto)
        If sel IsNot Nothing Then Return sel.iata
        Dim t As String = If(cbo.Text, "").Trim().ToUpper()
        Return If(t.Length >= 3, t.Substring(0, 3), t)
    End Function

    ' --- Calendario de rango (fechas ida/vuelta) ---
    ' WPF no trae un selector de rango con dos clics sueltos y vista previa, asi
    ' que se maneja a mano: se interceptan el click y el movimiento del mouse
    ' sobre los dias. En modo ida y vuelta, el primer click fija la ida, el mouse
    ' va mostrando el rango tentativo, y el segundo click fija la vuelta.

    Private modoSoloIda As Boolean = False
    Private idaFijada As Date?   ' en modo ida y vuelta, la ida ya elegida

    Private Sub btnFechas_Click(sender As Object, e As RoutedEventArgs)
        calFechas.DisplayDateStart = Date.Today   ' no se eligen fechas pasadas
        popupFechas.IsOpen = True
    End Sub

    Private Sub btnListoFechas_Click(sender As Object, e As RoutedEventArgs)
        popupFechas.IsOpen = False
    End Sub

    Private Sub btnLimpiarFechas_Click(sender As Object, e As RoutedEventArgs)
        calFechas.SelectedDates.Clear()
        idaFijada = Nothing
        btnFechas.Content = "Elegí las fechas"
    End Sub

    Private Sub Modo_Cambiado(sender As Object, e As RoutedEventArgs)
        ' Los controles pueden no existir aun durante la carga inicial del XAML.
        modoSoloIda = (rbSoloIda IsNot Nothing AndAlso rbSoloIda.IsChecked = True)
        If calFechas IsNot Nothing Then calFechas.SelectedDates.Clear()
        idaFijada = Nothing
        If btnFechas IsNot Nothing Then btnFechas.Content = "Elegí las fechas"
        If txtAyudaFechas IsNot Nothing Then
            txtAyudaFechas.Text = If(modoSoloIda,
                "Tocá el día de salida.",
                "Tocá la ida y después la vuelta (entre medio se va marcando el rango).")
        End If
    End Sub

    ' Click sobre un dia.
    Private Sub calFechas_PreviewMouseUp(sender As Object, e As MouseButtonEventArgs)
        Dim dia As Date? = DiaBajoCursor(e)
        If Not dia.HasValue Then Return    ' click en flechas/encabezado: dejar pasar
        e.Handled = True                   ' se maneja aca, no la seleccion nativa
        Dim d As Date = dia.Value

        If modoSoloIda Then
            idaFijada = Nothing
            FijarSeleccion(d, Nothing)
            popupFechas.IsOpen = False
            Return
        End If

        If Not idaFijada.HasValue Then
            idaFijada = d
            FijarSeleccion(d, Nothing)
        ElseIf d < idaFijada.Value Then
            idaFijada = d                  ' segundo click antes de la ida: nueva ida
            FijarSeleccion(d, Nothing)
        Else
            FijarSeleccion(idaFijada.Value, d)
            idaFijada = Nothing
            popupFechas.IsOpen = False
        End If
    End Sub

    ' Vista previa del rango mientras se mueve el mouse, despues de fijar la ida.
    Private Sub calFechas_PreviewMouseMove(sender As Object, e As MouseEventArgs)
        If modoSoloIda OrElse Not idaFijada.HasValue Then Return
        Dim dia As Date? = DiaBajoCursor(e)
        If Not dia.HasValue Then Return
        If dia.Value >= idaFijada.Value Then
            FijarSeleccion(idaFijada.Value, dia.Value)
        Else
            FijarSeleccion(idaFijada.Value, Nothing)
        End If
    End Sub

    ' Si el mouse sale del calendario a mitad de eleccion, se deja marcada la ida.
    Private Sub calFechas_MouseLeave(sender As Object, e As MouseEventArgs)
        If Not modoSoloIda AndAlso idaFijada.HasValue Then
            FijarSeleccion(idaFijada.Value, Nothing)
        End If
    End Sub

    ' Encuentra el dia (fecha) del boton del calendario que esta bajo el cursor.
    Private Function DiaBajoCursor(e As MouseEventArgs) As Date?
        Dim obj As DependencyObject = TryCast(e.OriginalSource, DependencyObject)
        While obj IsNot Nothing AndAlso Not (TypeOf obj Is CalendarDayButton)
            obj = VisualTreeHelper.GetParent(obj)
        End While
        Dim btn As CalendarDayButton = TryCast(obj, CalendarDayButton)
        If btn Is Nothing OrElse Not btn.IsEnabled Then Return Nothing
        If TypeOf btn.DataContext Is Date Then Return CType(btn.DataContext, Date)
        Return Nothing
    End Function

    ' Aplica la seleccion al calendario (resaltado) y actualiza el texto del boton.
    Private Sub FijarSeleccion(ida As Date, vuelta As Date?)
        calFechas.SelectedDates.Clear()
        If vuelta.HasValue Then
            calFechas.SelectedDates.AddRange(ida, vuelta.Value)
            btnFechas.Content = ida.ToString("dd/MM/yyyy") & "  →  " & vuelta.Value.ToString("dd/MM/yyyy")
        Else
            calFechas.SelectedDates.Add(ida)
            btnFechas.Content = ida.ToString("dd/MM/yyyy") & If(modoSoloIda, "  (solo ida)", "  →  …")
        End If
    End Sub

    ' Lee lo elegido para armar la consulta. Ida = mas temprana, vuelta = mas tardia.
    Private Function RangoElegido() As (ida As Date?, vuelta As Date?)
        Dim ds = calFechas.SelectedDates.OrderBy(Function(d) d).ToList()
        If ds.Count = 0 Then Return (Nothing, Nothing)
        If ds.Count = 1 Then Return (ds(0), CType(Nothing, Date?))
        Return (ds.First(), ds.Last())
    End Function

    Private Async Sub btnBuscar_Click(sender As Object, e As RoutedEventArgs)
        Dim origen As String = ObtenerIata(cboOrigen)
        Dim destino As String = ObtenerIata(cboDestino)
        Dim fechas = RangoElegido()

        ' Validacion minima en el cliente; el resto de las reglas las aplica el backend.
        If origen = "" OrElse destino = "" OrElse Not fechas.ida.HasValue Then
            txtEstado.Text = "Elegí origen, destino y las fechas."
            Return
        End If

        Dim invariante = Globalization.CultureInfo.InvariantCulture
        Dim consulta As New Dictionary(Of String, Object) From {
            {"origen", origen},
            {"destino", destino},
            {"fecha", fechas.ida.Value.ToString("dd/MM/yyyy", invariante)},
            {"adultos", If(cboAdultos.SelectedItem, 1)}
        }
        If fechas.vuelta.HasValue Then
            consulta("fecha_vuelta") = fechas.vuelta.Value.ToString("dd/MM/yyyy", invariante)
        End If
        Dim aero As Aerolinea = TryCast(cboAerolinea.SelectedItem, Aerolinea)
        If aero IsNot Nothing Then consulta("aerolinea") = aero.clave

        ' Estado "buscando": se bloquea el boton para no disparar dos consultas juntas.
        btnBuscar.IsEnabled = False
        btnBuscar.Content = "Buscando..."
        txtEstado.Text = ""
        panelResumen.Visibility = Visibility.Collapsed
        grdTramos.ItemsSource = Nothing

        Try
            Dim r As Respuesta = Await ClienteApi.BuscarAsync(consulta)
            MostrarResultado(r)
        Catch ex As Exception
            txtEstado.Text = "No se pudo conectar con el backend: " & ex.Message
        Finally
            btnBuscar.IsEnabled = True
            btnBuscar.Content = "Buscar mejor vuelo"
        End Try
    End Sub

    ' Contempla las tres formas de respuesta del backend: error, sin resultados,
    ' y la recomendacion con datos.
    Private Sub MostrarResultado(r As Respuesta)
        If r Is Nothing Then
            txtEstado.Text = "El backend devolvió una respuesta vacía."
            Return
        End If
        If Not r.ok Then
            txtEstado.Text = $"No se pudo buscar ({r.motivo}): {r.[error]}"
            Return
        End If
        If r.mejor Is Nothing Then
            txtEstado.Text = If(r.mensaje, "No se encontraron vuelos para esas fechas.")
            Return
        End If

        txtResumen.Text = $"{r.mejor.millas:N0} millas  +  $ {r.mejor.impuestos:N0} en impuestos"
        txtAnalisis.Text = r.analisis
        If r.eleccion_por_ia Then
            txtNota.Visibility = Visibility.Collapsed
        Else
            txtNota.Text = "(La IA no respondió; se eligió por la regla de menos millas.)"
            txtNota.Visibility = Visibility.Visible
        End If
        panelResumen.Visibility = Visibility.Visible
        grdTramos.ItemsSource = r.mejor.tramos
    End Sub

End Class

Imports System.Threading.Tasks

' Ventana principal. Toma lo que carga el usuario, se lo manda al backend y
' muestra la recomendacion. La logica de red y los modelos estan en ClienteApi.vb.
Class MainWindow

    Public Sub New()
        InitializeComponent()
        ' Combo de adultos: 1 a 9 (lo que acepta la API).
        For i As Integer = 1 To 9
            cboAdultos.Items.Add(i)
        Next
        cboAdultos.SelectedIndex = 0
    End Sub

    ' Al abrirse la ventana se piden las aerolineas para llenar el combo.
    Private Async Sub Window_Loaded(sender As Object, e As RoutedEventArgs)
        Await CargarAerolineas()
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

    Private Async Sub btnBuscar_Click(sender As Object, e As RoutedEventArgs)
        ' Validacion minima en el cliente; el resto de las reglas las aplica el backend.
        If txtOrigen.Text.Trim() = "" OrElse txtDestino.Text.Trim() = "" OrElse txtFecha.Text.Trim() = "" Then
            txtEstado.Text = "Completá al menos origen, destino y fecha de ida."
            Return
        End If

        Dim consulta As New Dictionary(Of String, Object) From {
            {"origen", txtOrigen.Text.Trim().ToUpper()},
            {"destino", txtDestino.Text.Trim().ToUpper()},
            {"fecha", txtFecha.Text.Trim()},
            {"adultos", If(cboAdultos.SelectedItem, 1)}
        }
        If txtVuelta.Text.Trim() <> "" Then consulta("fecha_vuelta") = txtVuelta.Text.Trim()
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

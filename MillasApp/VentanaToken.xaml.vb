Imports System.Windows.Media

' Ventanita para pegar un token nuevo de Aerolineas sin editar archivos.
' Muestra el estado del token actual y guarda el que se pegue (POST /token).
Class VentanaToken

    Private Async Sub Window_Loaded(sender As Object, e As RoutedEventArgs)
        Await MostrarEstado()
    End Sub

    Private Async Function MostrarEstado() As Task
        Try
            Dim est As EstadoToken = Await ClienteApi.EstadoTokenAsync()
            If est Is Nothing OrElse Not est.hay_token Then
                txtEstado.Text = "No hay ningún token cargado todavía."
                txtEstado.Foreground = New SolidColorBrush(Color.FromRgb(&HC0, &H39, &H2B))
            ElseIf est.vencido Then
                txtEstado.Text = $"El token actual está VENCIDO (venció el {est.vence}). Pegá uno nuevo."
                txtEstado.Foreground = New SolidColorBrush(Color.FromRgb(&HC0, &H39, &H2B))
            Else
                txtEstado.Text = $"Token vigente. Vence el {est.vence} (quedan ~{est.minutos} min)."
                txtEstado.Foreground = New SolidColorBrush(Color.FromRgb(&H1B, &H7F, &H3B))
            End If
        Catch ex As Exception
            txtEstado.Text = "No me pude conectar con el backend para ver el estado. ¿Está corriendo?"
            txtEstado.Foreground = New SolidColorBrush(Color.FromRgb(&HC0, &H39, &H2B))
        End Try
    End Function

    Private Async Sub btnGuardar_Click(sender As Object, e As RoutedEventArgs)
        Dim token As String = txtToken.Text.Trim()
        If token = "" Then
            Mensaje("Pegá el token antes de guardar.", esError:=True)
            Return
        End If

        btnGuardar.IsEnabled = False
        Try
            Dim r As EstadoToken = Await ClienteApi.GuardarTokenAsync(token)
            If r IsNot Nothing AndAlso r.ok Then
                Mensaje($"¡Listo! Token guardado. Vence el {r.vence} (~{r.minutos} min).", esError:=False)
                txtToken.Clear()
                Await MostrarEstado()
            Else
                Dim detalle As String = If(r IsNot Nothing, r.error, "respuesta vacía del backend")
                Mensaje("No se pudo guardar: " & detalle, esError:=True)
            End If
        Catch ex As Exception
            Mensaje("No me pude conectar con el backend: " & ex.Message, esError:=True)
        Finally
            btnGuardar.IsEnabled = True
        End Try
    End Sub

    Private Sub Mensaje(texto As String, esError As Boolean)
        txtMensaje.Text = texto
        txtMensaje.Foreground = New SolidColorBrush(
            If(esError, Color.FromRgb(&HC0, &H39, &H2B), Color.FromRgb(&H1B, &H7F, &H3B)))
        txtMensaje.Visibility = Visibility.Visible
    End Sub

    Private Sub btnCerrar_Click(sender As Object, e As RoutedEventArgs)
        Me.Close()
    End Sub

End Class

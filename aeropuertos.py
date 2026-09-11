"""Lista de aeropuertos que opera Aerolineas Argentinas, para el autocompletado.

La API de Aerolineas no expone (o no se encontro) un endpoint publico con el
catalogo de aeropuertos: los candidatos probados dieron 404. Como los
aeropuertos son estables y no cambian seguido, se mantiene esta lista curada.
Sirve para que la app de escritorio sugiera codigos IATA a partir de la ciudad
(ej. "bariloche" -> BRC, "buenos aires" -> EZE y AEP).

Si algun dia aparece el endpoint real, se reemplaza la fuente de `catalogo()`
sin tocar la app: ella solo consume GET /aeropuertos.

Cada entrada: codigo IATA, ciudad, pais y nombre del aeropuerto. `ciudad` es la
clave del autocompletado; por eso EZE y AEP comparten "Buenos Aires". `pais`
arma el texto que muestra la app, al estilo "Buenos Aires, Argentina (AEP)".
"""

# (iata, ciudad, pais, nombre)
_DATOS = [
    # --- Cabotaje (Argentina) ---
    ("AEP", "Buenos Aires", "Argentina", "Aeroparque Jorge Newbery"),
    ("EZE", "Buenos Aires", "Argentina", "Ezeiza - Ministro Pistarini"),
    ("COR", "Cordoba", "Argentina", "Ingeniero Ambrosio Taravella"),
    ("MDZ", "Mendoza", "Argentina", "El Plumerillo"),
    ("BRC", "San Carlos de Bariloche", "Argentina", "Teniente Luis Candelaria"),
    ("ROS", "Rosario", "Argentina", "Islas Malvinas"),
    ("IGR", "Puerto Iguazu", "Argentina", "Cataratas del Iguazu"),
    ("SLA", "Salta", "Argentina", "Martin Miguel de Guemes"),
    ("TUC", "San Miguel de Tucuman", "Argentina", "Teniente Benjamin Matienzo"),
    ("FTE", "El Calafate", "Argentina", "Comandante Armando Tola"),
    ("USH", "Ushuaia", "Argentina", "Malvinas Argentinas"),
    ("NQN", "Neuquen", "Argentina", "Presidente Peron"),
    ("BHI", "Bahia Blanca", "Argentina", "Comandante Espora"),
    ("CRD", "Comodoro Rivadavia", "Argentina", "General Enrique Mosconi"),
    ("REL", "Trelew", "Argentina", "Almirante Marcos A. Zar"),
    ("RGL", "Rio Gallegos", "Argentina", "Piloto Norberto Fernandez"),
    ("JUJ", "San Salvador de Jujuy", "Argentina", "Gobernador Horacio Guzman"),
    ("PSS", "Posadas", "Argentina", "Libertador General San Martin"),
    ("RES", "Resistencia", "Argentina", "Resistencia"),
    ("CTC", "Catamarca", "Argentina", "Coronel Felipe Varela"),
    ("SDE", "Santiago del Estero", "Argentina", "Vicecomodoro Angel de la Paz Aragones"),
    ("AFA", "San Rafael", "Argentina", "Suboficial Ayudante Santiago German"),
    ("MDQ", "Mar del Plata", "Argentina", "Astor Piazzolla"),
    ("LUQ", "San Luis", "Argentina", "Brigadier Mayor Cesar Raul Ojeda"),
    ("IRJ", "La Rioja", "Argentina", "Capitan Vicente Almandos Almonacid"),
    ("CPC", "San Martin de los Andes", "Argentina", "Aviador Carlos Campos - Chapelco"),
    ("RGA", "Rio Grande", "Argentina", "Gobernador Ramon Trejo Noel"),
    ("PMY", "Puerto Madryn", "Argentina", "El Tehuelche"),
    ("CNQ", "Corrientes", "Argentina", "Doctor Fernando Piragine Niveyro"),
    ("FMA", "Formosa", "Argentina", "Formosa"),
    ("VDM", "Viedma", "Argentina", "Gobernador Edgardo Castello"),
    ("EQS", "Esquel", "Argentina", "Brigadier General Antonio Parodi"),
    ("RSA", "Santa Rosa", "Argentina", "Santa Rosa"),
    ("PRA", "Parana", "Argentina", "General Justo Jose de Urquiza"),
    ("SFN", "Santa Fe", "Argentina", "Sauce Viejo"),
    # --- Internacionales frecuentes de Aerolineas ---
    ("MAD", "Madrid", "Espana", "Adolfo Suarez Madrid-Barajas"),
    ("MIA", "Miami", "Estados Unidos", "Miami International"),
    ("JFK", "Nueva York", "Estados Unidos", "John F. Kennedy"),
    ("GRU", "San Pablo", "Brasil", "Guarulhos"),
    ("GIG", "Rio de Janeiro", "Brasil", "Galeao"),
    ("SCL", "Santiago de Chile", "Chile", "Arturo Merino Benitez"),
    ("MVD", "Montevideo", "Uruguay", "Carrasco"),
    ("LIM", "Lima", "Peru", "Jorge Chavez"),
    ("BOG", "Bogota", "Colombia", "El Dorado"),
    ("CUN", "Cancun", "Mexico", "Cancun"),
    ("PUJ", "Punta Cana", "Republica Dominicana", "Punta Cana"),
    ("ASU", "Asuncion", "Paraguay", "Silvio Pettirossi"),
    ("MEX", "Ciudad de Mexico", "Mexico", "Benito Juarez"),
    ("FCO", "Roma", "Italia", "Leonardo da Vinci - Fiumicino"),
]


def catalogo() -> list[dict]:
    """Lista de aeropuertos como dicts, para el endpoint /aeropuertos."""
    return [{"iata": iata, "ciudad": ciudad, "pais": pais, "nombre": nombre}
            for iata, ciudad, pais, nombre in _DATOS]

# ADR-002 — El catálogo se enriquece leyendo la ficha web del MINCETUR

| | |
|---|---|
| **Estado** | Aceptada e implementada |
| **Fecha** | 30 de agosto de 2026 |
| **Incremento** | 1 — catálogo integrado (refuerza la brecha 1) |
| **Atributo de calidad principal** | **Fiabilidad** (completitud de los datos) |
| **Atributos secundarios** | Rendimiento (caché en disco), mantenibilidad |
| **Nota de origen** | [`2026-08-30-la-ficha-web-traia-lo-que-el-csv-no.md`](../decisiones/2026-08-30-la-ficha-web-traia-lo-que-el-csv-no.md) |

---

## Contexto

Durante seis fases el proyecto declaró dos limitaciones **como si fueran de la
fuente**, y las imprimió en el README y en la documentación de incrementos:

> «El inventario del MINCETUR no publica horarios.»
> «El inventario del MINCETUR no trae descripciones.»

Las dos eran **verdad del CSV** y **falsas de la fuente**. Cada recurso del
inventario tiene además una **ficha web** en el propio sistema del MINCETUR,
cuya dirección estaba guardada en la columna `url_ficha` **desde la Fase 1** y
se mostraba como enlace en la pantalla de detalle. Nadie había abierto una.

Dentro hay: descripción larga, horario de visita, tipo de ingreso, época
propicia y **conteos reales de visitantes** con su fuente y su año.

## Decisión

Se añade una **segunda vía de ingesta** sobre la misma fuente oficial:
`utilidades/fichas_mincetur.py` descarga y parsea las 295 fichas web, y
`utilidades/cargar_fichas.py` vuelca a la base lo que el CSV no trae.

Cuatro reglas de diseño del lector, todas con motivo:

1. **Espera un segundo entre peticiones.** Son 295 páginas de un servicio
   público; degradarlo sería trasladarle a un tercero el coste de nuestra prisa.
2. **Guarda cada página en disco.** Reejecutar el guion no genera ni una
   petición nueva: la segunda ejecución tarda cero.
3. **Se identifica en el `User-Agent`** diciendo qué es y para qué.
4. **Busca las tablas por su cabecera, no por su posición.** Las fichas sin
   visitantes no traen esa tabla y todo lo de abajo se corre un puesto: buscar
   «la cuarta tabla» habría devuelto el horario de otra cosa en la mitad de los
   casos.

**No se rellena lo que la ficha no dice.** Lo ausente queda nulo y el guion
informa de cuántas fichas faltó cada dato.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Dejar la limitación declarada tal como estaba** | Era falsa. Mantenerla habría dejado dos afirmaciones incorrectas en documentos entregables. |
| **Rellenar los horarios ausentes con un supuesto** («abre de 9 a 17») | Presentaría como dato una invención, en el proyecto cuyo eje es no inventar. El 29 % sigue sin horario y el itinerario lo avisa. |
| **Descargar las fichas en cada arranque** | 295 peticiones al Estado por cada despliegue. La caché en disco lo evita. |
| **Convertir las fechas de fiesta a un día exacto** | Muchas son móviles («el último domingo de enero»). Exigiría calcular el calendario litúrgico y adivinar lo que la ficha no dice. Se guarda la frase literal y los meses. |
| **Rechazar toda frase con marca de pasado** al extraer fechas | Se probó: dejó **las 36 fiestas sin fecha**, porque casi toda descripción menciona algún año. Se sustituyó por puntuación por frase. |

## Consecuencias

**Positivas, medidas sobre 295 fichas leídas y 0 fallidas**

| Dato | Antes | Ahora |
|---|---|---|
| Descripciones | 0 | **295** (100 %) |
| Horarios | 0 | **208** (71 %) |
| Tipo de ingreso | 0 | **210** (71 %) |
| Conteos de visitantes | 0 | **414 filas** en 207 recursos |
| Fiestas con fecha | 0 | **28** de 36 |

La afluencia dejó de calcularse solo con reglas de calendario: el Centro
Piscícola El Ingenio tiene **120 889 visitantes locales en 2023** publicados por
el MINCETUR.

**Negativas, y asumidas**

- El 29 % de los recursos sigue sin horario y 8 fiestas sin fecha.
- El parser depende del HTML del MINCETUR: si cambia la maquetación, hay que
  ajustarlo. Buscar por cabecera reduce el riesgo pero no lo elimina.
- Tres fallos propios aparecieron construyéndolo, todos documentados: «Julio»
  interpretado como mes cuando era un nombre de persona; la historia del pueblo
  aportando meses falsos; y expresiones regulares escritas sin `r"..."`, que
  **dejaron de reconocer nada sin dar ningún error**.

## La lección que deja, y que es la más transferible del proyecto

> **«La fuente no lo publica» hay que comprobarlo antes de escribirlo.** Una
> limitación declarada es una afirmación como cualquier otra: hay que poder
> enseñar en qué se apoya. Esta se apoyaba en no haber mirado.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_fichas_y_temporada.py -v
```

## Relacionado

- [ADR-001 — Fuente del catálogo](ADR-001-fuente-del-catalogo-inventario-mincetur.md)
- [ADR-013 — Los avisos viajan como código y parámetros](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md)

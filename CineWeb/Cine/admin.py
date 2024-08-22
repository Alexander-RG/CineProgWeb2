from django.contrib import admin
from .models import Pelicula, Genero, Sala, Funcion, Clasificacion, Asiento, Formato

# Register your models here.



class PeliculaAdmin(admin.ModelAdmin):
    list_display = ('Titulo',"Lanzamiento","formato_duracion", "generos_list")
    
    def formato_duracion(self,obj):
        horas = obj.Duracion // 60
        minutos = obj.Duracion % 60
        return f"{horas}:{minutos:02d}h"
    formato_duracion.short_description = "Duracion"
    
    def generos_list(self, obj):
        return ", ".join(Genero.Genero for Genero in obj.Genero.all()) 
    generos_list.short_description = "Generos"
class GeneroAdmin(admin.ModelAdmin):
    list_display = ('Genero',)
    
class FormatoAdmin(admin.ModelAdmin):
    list_display = ('Tipo',)

class SalaAdmin(admin.ModelAdmin):
    list_display = ('Nombre','Formato')

class ClasificacionAdmin(admin.ModelAdmin):
    list_display = ('Clase'),
    
class FuncionAdmin(admin.ModelAdmin):
    list_display = ('IdFuncion', 'get_pelicula_titulo', 'get_sala_nombre', 'Horario', 'Precio')

    def get_pelicula_titulo(self, obj):
        return obj.IdPelicula.Titulo
    get_pelicula_titulo.short_description = 'Película'

    def get_sala_nombre(self, obj):
        return obj.IdSala.Nombre
    get_sala_nombre.short_description = 'Sala'

class AsientoAdmin(admin.ModelAdmin):
    list_display = ('formato_posicion', 'get_sala_nombre','Fila','Numero')
    
    def get_sala_nombre(self, obj):
        return obj.IdSala.Nombre
    get_sala_nombre.short_description = 'Sala'
    
    def formato_posicion(self,obj):
        fila = obj.Fila
        numero = obj.Numero
        return f"{fila}{numero}"
    formato_posicion.short_description = "Posicion"

admin.site.register(Pelicula, PeliculaAdmin)
admin.site.register(Genero, GeneroAdmin)
admin.site.register(Sala, SalaAdmin)
admin.site.register(Funcion, FuncionAdmin)
admin.site.register(Clasificacion, ClasificacionAdmin)
admin.site.register(Asiento, AsientoAdmin)
admin.site.register(Formato, FormatoAdmin)
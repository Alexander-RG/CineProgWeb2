import json

from django.contrib.auth import authenticate, logout, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from .forms import RegistroUsuarioForm
from django.contrib.auth.models import Group
from .models import Pelicula, Funcion, Asiento, Reserva
from .forms import UserProfileForm
import qrcode
from io import BytesIO
from django.core.files import File
import google.generativeai as genai




def inicio(request):
    # Ordenar por fecha de creación en orden descendente y obtener los últimos 10 registros
    peliculas = Pelicula.objects.all().order_by('Lanzamiento')[:10]
    return render(request, r'cine/inicio.html', {'peliculas': peliculas})


def iniciov2(request):
    peliculas_destacadas = Pelicula.objects.order_by('-Lanzamiento')[:3]
    todas_peliculas = Pelicula.objects.all()

    context = {
        'peliculas_destacadas': peliculas_destacadas,
        'todas_peliculas': todas_peliculas,
    }

    return render(request, r'cine/iniciov2.html', context)


def detalle_pelicula(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, pk=pelicula_id)
    print(pelicula.Trailer)
    funciones = Funcion.objects.filter(IdPelicula=pelicula, Horario__gte=timezone.now()).order_by('Horario')

    # Agrupar funciones por fecha
    funciones_por_fecha = {}
    for funcion in funciones:
        fecha = funcion.Horario.date()
        if fecha not in funciones_por_fecha:
            funciones_por_fecha[fecha] = []
        funciones_por_fecha[fecha].append(funcion)

    context = {
        'pelicula': pelicula,
        'funciones_por_fecha': funciones_por_fecha,
    }
    return render(request, r'cine/detalle_pelicula.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('iniciov2')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    return render(request, r'cine/login.html')

def logout_view(request):
    logout(request)
    return redirect('iniciov2')


def registro_usuario(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            grupo, _ = Group.objects.get_or_create(name='Usuarios')
            user.groups.add(grupo)
            messages.success(request, 'Usuario registrado exitosamente.')
            return redirect('iniciov2')
    else:
        form = RegistroUsuarioForm()
    return render(request, r'cine/registro.html', {'form': form})

@login_required
def seleccion_asientos(request, funcion_id):
    funcion = Funcion.objects.get(IdFuncion=funcion_id)
    asientos = Asiento.objects.filter(IdSala=funcion.IdSala)
    asientos_reservados = Reserva.asientos_reservados(funcion_id).values_list('pk', flat=True)

    context = {
        'funcion': funcion,
        'asientos': asientos,
        'asientos_reservados': list(asientos_reservados)
    }
    return render(request, 'cine/seleccionar_asientos.html', context)



@login_required
@csrf_exempt
@require_POST
def reservar_asientos(request):
    data = json.loads(request.body)
    funcion_id = data.get('funcion_id')
    asientos_ids = data.get('asientos_ids')

    try:
        funcion = Funcion.objects.get(IdFuncion=funcion_id)

        with transaction.atomic():
            # Verificar si algún asiento ya está reservado
            asientos_reservados = Reserva.asientos_reservados(funcion_id)
            for asiento_id in asientos_ids:
                if asientos_reservados.filter(IdAsiento=asiento_id).exists():
                    raise ValueError(f"El asiento {asiento_id} ya está reservado.")

            # Crear la reserva
            reserva = Reserva.objects.create(
                IdUsuario=request.user,
                IdFuncion=funcion
            )
            asientos = Asiento.objects.filter(IdAsiento__in=asientos_ids)
            reserva.Asientos.add(*asientos)

            # Generar el código QR
            qr_data = f"Reserva ID: {reserva.IdReserva}, Usuario: {request.user.username}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')

            # Guardar la imagen del código QR
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            filename = f'reserva_{reserva.IdReserva}.png'
            reserva.ReservaQR.save(filename, File(buffer), save=False)
            reserva.save()

        return JsonResponse({'status': 'success', 'message': 'Reserva realizada con éxito'})

    except Funcion.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'La función no existe'}, status=404)
    except Asiento.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Uno o más asientos no existen'}, status=404)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Error al realizar la reserva'}, status=500)


@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect('logout')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, r'cine/editar_perfil.html', {'form': form})


def reservas_usuario(request):
    reservas = Reserva.objects.filter(IdUsuario=request.user).order_by('-FechaReserva')
    context = {
        'reservas': reservas
    }
    return render(request, r'cine/reservas_usuario.html', context)


genai.configure(api_key='AIzaSyC0IqS_GFpapID1tOhZsdqZtVai4BJGyS8')



@require_http_methods(["GET", "POST"])
def chat_ia(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '')

        model = genai.GenerativeModel("gemini-1.5-flash")

        personalidad = """
        Eres una IA experta en cine para ayudar a los clientes de Cine Aester, tu nombre es CinIa y tu mision es ayudarles a elegir una pelicula
        o darles recomendaciones segun sus necesidades, no te desvies del tema principal que es el cine y demas, ten una personalidad agradable y 
        tambien da respuestas no tan largas sino concisas con tu humor si es necesario, no es necesario que te presentes cada vez, solo si te lo preguntan 
        y cocentrate a responder la pregunta que te hacen
        
        """

        # Combina las instrucciones del sistema con el mensaje del usuario
        full_prompt = f"{personalidad}\n\nUsuario: {user_message}\nCineBot:"

        response = model.generate_content(full_prompt)

        return JsonResponse({'bot_response': response.text})

    return render(request, 'cine/chatia.html')
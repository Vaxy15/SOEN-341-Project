from django.http import HttpResponse

def home(request):
    return HttpResponse("Campus Events app is working ✅")

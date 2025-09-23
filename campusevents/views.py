from django.http import HttpResponse

def home(_request):
    return HttpResponse("Campus Events app is working ✅")

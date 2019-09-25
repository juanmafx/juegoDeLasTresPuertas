# Las tres puertas *-
import random

w=0; # Veces que ganas sin cambiar de puerta
wc=0 # Veces que gana Cambiando de puerta
vps=0 # Veces que Pierde sin cambiar de puerta
vpc=0 # Veces que Pierde Vambiando de puerta

for i in range(1000):
    pe=random.randrange(1,4)
    pp=random.randrange(1,4)
    
    if pe == pp:
        w=w+1
    else:
        vps =vps+1
       
    if pe == 1 and pp==1:
        vpc=vpc+1
    
    if pe == 2 and pp==2:
        vpc=vpc+1
    
    if pe == 3 and pp==3:
        vpc=vpc+1

    if pe == 2 and pp==1:
        wc=wc+1
    
    if pe == 3 and pp==1:
        wc=wc+1   
        
    if pe == 1 and pp==2:
        wc=wc+1
    
    if pe == 3 and pp==2:
        wc=wc+1
     
    if pe == 1 and pp==3:
        wc=wc+1
    
    if pe == 2 and pp==3:
        wc=wc+1

print("Gano ",w, " sin cambiar de puerta.")
print("Gano ",wc, " cambiando de puerta.")
print("Veces que gano + veces que perdio sin cambiar de puerta ",w + vps)
print("Veces que gano + veces que perdio cambiando de puerta ",wc + vpc)

# Adeas se puede demosrar que la simulacion es conrecta en la suenguie linea.

print('La suma de ganadas cambiando de puerta ',w,' mas  las ganadas sin cambiar de puerta',wc ,'es = ',w+wc,'Que es igual al numero de ciclos')

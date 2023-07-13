import numpy as np
import pandas as pd
import argparse
from PIL import Image
from skimage import io
import os
import branca
import time



#Input of the script
parser = argparse.ArgumentParser()
parser.add_argument('--folder_data',  type=str,required=True,  help='Folder where the CSV files of the figures are located')
parser.add_argument('--tile',  type=str,  help='Tile pisition. Format example: [1,2]')
parser.add_argument('--zoom',  type=int,required=True,  help='Zoom level')
parser.add_argument('--output', '--out',  type=str,required=True,  help='Filename where you want to save the data')
args = parser.parse_args()

folder = args.folder_data
tile=args.tile
if tile:
    tile=np.array(tile[1:-1].split(',')).astype('int')
    x_tile = tile[0]
    y_tile = tile[1]

zoom = args.zoom
output = args.output


# De bits a magnitudes
def bits_a_mag(bits):
    bits=bits.astype('float')
    bits[bits==255]=np.nan
    return bits/20+14

# De radiación a magnitudes
def radiacion_a_mag(rad):
    a=np.round(np.log10(rad)*-0.95+20.93,2)
    a[rad==0]=22
    a[a>22]=22
    return a

# De magnitudes a bits
def mag_a_bits(mag):
    a=np.round((mag-14)*20)
    a[np.isnan(a)]=255
    return a.astype('int')   

def grado_a_radianes(alfa):
    return alfa*2*np.pi/360

def radianes_a_grado(alfa):
    return alfa*360/(2*np.pi)

def equirectangular_to_mercator(longitude,latitude,zoom):
    longitude=grado_a_radianes(longitude)
    latitude=grado_a_radianes(latitude)

    x=256*2**zoom*(np.pi+longitude)/(2*np.pi)
    y=256*2**zoom*(np.pi-np.log(np.tan(np.pi/4+latitude/2)))/(2*np.pi)
    return x,y

def equirectangular_to_mercator_sin_zoom(longitude,latitude):
    longitude=grado_a_radianes(longitude)
    latitude=grado_a_radianes(latitude)

    x=256*(np.pi+longitude)/(2*np.pi)
    y=256*(np.pi-np.log(np.tan(np.pi/4+latitude/2)))/(2*np.pi)
    return x,y

def mercator_to_equirectangular(x,y,zoom):
    longitude=2*np.pi*x/(256*2**zoom)-np.pi
    latitude=2*np.arctan(np.exp(np.pi-2*np.pi*y/(256*2**zoom)))-np.pi/2

    return radianes_a_grado(longitude),radianes_a_grado(latitude)

def Tile(V): #Obtiene la tesela de equirectangular en la que se encuentran unas coordenadas
    lon=V[0]
    lat=V[1]
    v=np.floor((90-lat)/10)
    h=np.floor((lon+180)/10)
    return int(v),int(h)

def Esquina_superior_derecha(V): #Esquina superior derecha de una tesela equirectangular
    lat=90-V[1]*10
    lon=V[0]*10-180
    return lon,lat

def Add_zero(a):
    if a<10:
        return ('0'+str(a))
    else:
        return str(a)
    
def Datos_tesela(x,y,zoom): #Listado de teselas equireactangular necesarias para una tesela mercator
    esquina_izq_sup=Tile(mercator_to_equirectangular(x*256,y*256,zoom))
    esquina_der_inf=Tile(mercator_to_equirectangular(256*(x+1),256*(y+1),zoom))
    V=[]
    for i in range(esquina_izq_sup[0],esquina_der_inf[0]+1):
        for ii in range(esquina_izq_sup[1],esquina_der_inf[1]+1):
            V=V+['h'+Add_zero(ii)+'v'+Add_zero(i)]
    return V

def Nombre_a_tesela(name):
    return int(name[1:3]),int(name[4:])

def Anadir_pixeles(DF2):
    fx=np.array(list(set(range(DF2['X'].min(),DF2['X'].min()+256))-set(DF2['X'].values)))-DF2['X'].min()
    fy=np.array(list(set(range(DF2['Y'].min(),DF2['Y'].min()+256))-set(DF2['Y'].values)))-DF2['Y'].min()
    fy.sort()
    mag=DF2['mag'].values.reshape([len(set(DF2['X'])),len(set(DF2['Y']))])
    for i in fy:
        mag=np.insert(mag, i, mag[:,i-1], 1)
    for i in fx:
        mag=np.insert(mag, i, mag[i-1,:], 0)
    X=np.transpose(np.tile(np.array(range(DF2['X'].min(),DF2['X'].min()+256)),(256,1)))
    Y=np.tile(np.array(range(DF2['Y'].min(),DF2['Y'].min()+256)),(256,1))
    return pd.DataFrame({'X':X.reshape([-1]),'Y':Y.reshape([-1]),'mag':mag.reshape([-1])})

Colores=__mag_colors = [
    "#FFFFFF",  # 14
    "#FFFDFF",
    "#FFFBFF",
    "#FFF9FF",
    "#FFF7FF",
    "#FFF5FF",
    "#FFF3FF",
    "#FFF1FF",
    "#FFEFFF",
    "#FFEDFF",
    "#FFEBFF",
    "#FFE9FF",
    "#FFE7FF",
    "#FFE5FF",
    "#FFE2FF",
    "#FFE0FE",
    "#FFDFFC",
    "#FFDEFA",
    "#FFDDF8",
    "#FFDCF6",
    "#FDDBF4",  # 15
    "#FDDBEE",
    "#FDDBF1",
    "#FDDCEC",
    "#FDDDEA",
    "#FDDEE8",
    "#FDE0E6",
    "#FDE2E5",
    "#FDE4E4",
    "#FDE6E3",
    "#FDE8E3",
    "#FDEAE1",
    "#FDECE0",
    "#FDEEDF",
    "#FDF0DE",
    "#FDF2DD",
    "#FDF4DC",
    "#FDF5DB",
    "#FDF6DA",
    "#FCF6D9",
    "#FAF6D8",  # 16
    "#F8F7D8",
    "#F6F8D8",
    "#F4F9D7",
    "#F2FAD7",
    "#F0FBD6",
    "#EEFCD6",
    "#ECFDD6",
    "#EAFED6",
    "#E8FFD6",
    "#E6FFD8",
    "#E4FFDA",
    "#E2FFDC",
    "#E0FFDE",
    "#DFFFE0",
    "#DEFFE2",
    "#DDFFE4",
    "#DCFFE6",
    "#DBFFE8",
    "#DAFFEA",
    "#D9FFEC",  # 17
    "#D9FEEE",
    "#D9FDF0",
    "#D9FCF2",
    "#D9FBF4",
    "#D9FAF6",
    "#D9F9F8",
    "#D9F8FA",
    "#D9F7FC",
    "#D9F6FE",
    "#D8F4FE",
    "#D7F2FE",
    "#D6F0FD",
    "#D5EDFC",
    "#D4EAFB",
    "#D3E7FA",
    "#D2E4F9",
    "#D1E1F8",
    "#D0DEF7",
    "#CFDAF7",
    "#CFD4F8",  # 18
    "#CFC8F6",
    "#D0BAF4",
    "#D1AAF2",
    "#D39AEE",
    "#D58AE9",
    "#D77CE0",
    "#D970D6",
    "#DB68CB",
    "#DD61BB",
    "#DF5AAC",
    "#E0539D",
    "#E04B8C",
    "#DE437B",
    "#DC3B6A",
    "#DA335D",
    "#D82C50",
    "#D62644",
    "#D42238",
    "#D21E31",
    "#D01A2B",  # 19
    "#CE222A",
    "#CC2B29",
    "#CB3428",
    "#CB4327",
    "#CD4E26",
    "#D25A25",
    "#D86824",
    "#DE7823",
    "#E48A22",
    "#E89E21",
    "#EEAB20",
    "#F2B71F",
    "#F6C31E",
    "#FECD1E",
    "#F8D11F",
    "#EBCE20",
    "#DEC921",
    "#CCC521",
    "#BAC221",
    "#A8BE21",  # 20
    "#94BC21",
    "#7FBA23",
    "#6CB928",
    "#58B92D",
    "#4CBA36",
    "#42BC40",
    "#3ABE4C",
    "#35C05B",
    "#32C26A",
    "#2FC578",
    "#2CC886",
    "#28C994",
    "#24C8A3",
    "#21C5B0",
    "#1EC1BD",
    "#1ABCC9",
    "#17B2D1",
    "#14A6D6",
    "#119ADA",
    "#118EDC",  # 21
    "#1382DC",
    "#1576DC",
    "#176ADC",
    "#195EDB",
    "#1B52D9",
    "#1D46D7",
    "#1F3AD5",
    "#212ED3",
    "#2324D1",
    "#261CCE",
    "#2D19CB",
    "#341AC8",
    "#3B1BC4",
    "#421DBF",
    "#491FBA",
    "#5021B4",
    "#5523AB",
    "#5825A2",
    "#5B2799",
    "#5D2A90",  # 22
    "#5C2E87",
    "#5A337E",
    "#583875",
    "#553B6C",
    "#523E63",
    "#4F3F5A",
    "#4C3F51",
    "#493C49",
    "#463842",
    "#44333C",
    "#422E36",
    "#402A30",
    "#3E262B",
    "#3C2427",
    "#3A2224",
    "#382021",
    "#361E1F",
    "#341C1D",
    "#321A1B",
    "#2E1919",  # 23
    "#2A1717",
    "#261515",
    "#221313",
    "#1E1111",
    "#1A0F0F",
    "#160D0D",
    "#120C0C",
    "#0E0B0B",
    "#0A0A0A",
    "#090909",
    "#080808",
    "#070707",
    "#060606",
    "#050505",
    "#040404",
    "#030303",
    "#020202",
    "#010101",
    "#000000",
]
Min_escala=14.0 #Minimo valor de escala 
Max_escala=24
Step_escala=len(Colores)*10#0 #10, 100 va más lento
cm=branca.colormap.LinearColormap(Colores,vmin=Min_escala, vmax=Max_escala).to_step(Step_escala)
inter=round((Max_escala-Min_escala)/Step_escala,10)
#Escala completa, valores
Leyenda_escala=[round(Min_escala+i*inter,10) for i in range(0,Step_escala+1)]
Colores_RGB=np.array(cm.colors)*255

def Dar_color(Z3):
    Z2=Z3.copy()
    Z2[Z2>-min(Leyenda_escala)]=-min(Leyenda_escala) #Trunca los maximos de brillo por el máximo brillo posible
    CZ=np.round(np.trunc(-Z2*1/inter)*inter,4) #Trunca al valor de la escala correspondiente segmentando por colores
    PZ=(CZ-Min_escala)/inter #Sabiendo el valor de la escala identifica la posición en el vector de la escala
    #Las tres matrices de cada color
    SIN_NULOS=PZ.copy()
    SIN_NULOS[np.isnan(SIN_NULOS)] = -max(Leyenda_escala)+inter #Lo nulos los pone como mínimos para evitar posibles fallos 
    RED=SIN_NULOS.copy().astype(int) 
    GREEN=SIN_NULOS.copy().astype(int)
    BLUE=SIN_NULOS.copy().astype(int)
    #Creción de la matriz de transparencia
    TRANS=PZ.copy()
    TRANS[TRANS>-100000000]=255
    TRANS[np.isnan(TRANS)] =0
    TRANS=TRANS.astype(int)
    #Bucle que cambia cada valor de posición por su correspondiente valor de color para RGB en matrices separadas
    for i in range(0,len(Colores_RGB)):
        RED[RED==i] =Colores_RGB[i][0]
        GREEN[GREEN==i] = Colores_RGB[i][1]
        BLUE[BLUE==i] = Colores_RGB[i][2]
        #if i%(len(Colores_RGB)/4)==0:
            #print(str(round(i/len(Colores_RGB)*100,1))+'%')
    #Redimensiona las matrices de colores para operar con ellas
    REDL=list(RED.reshape(-1,1))
    GREENL=list(GREEN.reshape(-1,1))
    BLUEL=list(BLUE.reshape(-1,1))
    TRANSL=list(TRANS.reshape(-1,1))
    Col_zeros=np.zeros(len(REDL)).reshape(-1,1) #Vector columna de ceros
    #Crea matrices de color 
    RED_M=np.append(np.append(np.append(REDL, Col_zeros, axis = 1), Col_zeros, axis = 1),Col_zeros, axis = 1)
    GREEN_M=np.append(np.append(np.append(Col_zeros, GREENL, axis = 1), Col_zeros, axis = 1),Col_zeros, axis = 1)
    BLUE_M=np.append(np.append(np.append(Col_zeros,Col_zeros, axis = 1), BLUEL, axis = 1),Col_zeros, axis = 1)
    TRANS_M=np.append(np.append(np.append(Col_zeros,Col_zeros, axis = 1), Col_zeros, axis = 1),TRANSL, axis = 1)
    #Obtenemos la matriz de color general
    Z_COLOR=RED_M+GREEN_M+BLUE_M+TRANS_M
    if len(RED.shape)>1:
        Z_COLOR=Z_COLOR.reshape(RED.shape[0],RED.shape[1],4)
    else:
        Z_COLOR=Z_COLOR
    Z_final=Z_COLOR.astype(int) #Convertimos en enteros para evitar probblmas por tipología
    return Z_final

def Generar_tesela(t1,t2,zoom):
    #inicio = time.time()
    out=output+"\mapa"+"\\tiles\\"+str(zoom)
    os.makedirs(out, exist_ok=True)
    DF=pd.DataFrame()

    #time1 = time.time()
    #print('t1')
    #print(time1-inicio)
    datos_tesela=Datos_tesela(t1,t2,zoom)

    for i in datos_tesela:
        #print('Longitud')
        #print(len(datos_tesela))
        nulos=False
        try:
            image=bits_a_mag(io.imread(folder+"\\"+i+".png"))
        except:
            image=np.full([2400, 2400], np.nan)
            nulos=True
        salir=False
        if nulos and len(datos_tesela)==1:
            salir=True
            break

        #time2 = time.time()
        #print('t2')
        #print(time2-time1)
        
        Esquina_sup_der=Esquina_superior_derecha(Nombre_a_tesela(i))
        LON=np.linspace(Esquina_sup_der[0],Esquina_sup_der[0]+10,image.shape[0])
        LAT=np.linspace(Esquina_sup_der[1],Esquina_sup_der[1]-10,image.shape[1])
        (X,Y)=equirectangular_to_mercator(LON,LAT,zoom)
        X=np.floor(X).astype('int')
        Y=np.floor(Y).astype('int')

        #time3 = time.time()
        #print('t3')
        #print(time3-time2)
       
        X1=np.tile(X, (1, 2400))[0]
        Y1=np.tile(Y, (1, 2400))[0]

        #TIME1 = time.time()
        #print('tt1')
        #print(TIME1-time3)

        Y1=np.transpose(Y1.reshape(2400,2400)).reshape([-1])

        #TIME2 = time.time()
        #print('tt2')
        #print(TIME2-TIME1)

        df=pd.DataFrame()
        df['mag']=image.reshape([-1])

        #TIME3 = time.time()
        #print('tt3')
        #print(TIME3-TIME2)

        df['X']=X1
        df['Y']=Y1
        df=df[(df['X']>=t1*256) & (df['Y']>=t2*256)]
        df=df[(df['X']<(t1+1)*256) & (df['Y']<(t2+1)*256)]
        df=df[(df['Y']>=0)]

        #TIME4 = time.time()
        #print('tt4')
        #print(TIME4-TIME3)
        
        #time4 = time.time()
        #print('t4')
        #print(time4-time3)    

        #print(df)  
       
        if df.shape[0]!=0:
            df=df.groupby(['X','Y']).mean()
            df2=pd.DataFrame(list(df.index))
            df2['mag']=df['mag'].values
            df2.columns=['X','Y','mag']
    
            DF=pd.concat([DF,df2])

        time5 = time.time()
        #print('t5')
        #print(time5-time4)
        #print(i)
    if salir:
        return 'exit'
    magnitudes=DF['mag']
    if list(magnitudes[~np.isnan(magnitudes)])!=[]:
        DF=DF.groupby(['X','Y']).mean()
        F=pd.DataFrame(list(DF.index))
        F['mag']=DF['mag'].values
        F.columns=['X','Y','mag']  
        F=Anadir_pixeles(F)
        F_C=-np.transpose(F['mag'].values.reshape([256,256]))
        F2=Dar_color(F_C)
        F2=Image.fromarray(F2.astype("uint8"))
        #fin = time.time()
        #print('t1')
        #print(fin-inicio)
        F2.save(out+"\h"+Add_zero(t1)+"v"+Add_zero(t2)+".png")
    #time6 = time.time()
    #print('t6')
    #print(time6-time5)

if tile:
    Generar_tesela(x_tile,y_tile,zoom)
else:
    cont=0
    for i in range(0,2**zoom):
        for ii in range(0,2**zoom):
            #inicio = time.time()
            Generar_tesela(i,ii,zoom)
            #fin = time.time()
            #print('T')
            #print(fin-inicio)
            cont=cont+1
            print(str(np.round(cont/(2**(2*zoom))*100,5))+'%')



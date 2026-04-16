
"""
Descarga de productos de APEC
"""
# ---------------------------------------------------------------------------- #
from datetime import datetime
import os
# ---------------------------------------------------------------------------- #
def Download(season, anio, descarga):
    if descarga=='Flechita':
         link_flechita = (f'https://www.apcc21.org/apcc_images/MME_FIG/ENSO_OUT/'
                          f'{season}/{anio}/Alert/ENSO_Alert.png')
         os.system('wget --no-cache -O enso_flechita_apec.png ' + link_flechita)
    elif descarga=='ENSO':
         link_prono_enso = (f'https://www.apcc21.org/apcc_images/MME_FIG/ENSO_OUT/'
                      f'{season}/{anio}/Probability/Prob_ENSO_Probability.png')
         os.system('wget --no-cache -O PronoENSO_APEC.png ' + link_prono_enso)
    elif descarga=='ENSO-Plume':
         link_prono_enso = (f'https://www.apcc21.org/apcc_images/MME_FIG/ENSO_OUT/'
                      f'{season}/{anio}/Timeseries/sst_Nino3.4.png')
         os.system('wget --no-cache -O Pluma_PronoENSO_APEC.png ' + link_prono_enso)
    elif descarga=='IOD':
          link_prono_iod = (f"https://www.apcc21.org/apcc_images/MME_FIG/ENSO_OUT/"
                            f"{season}/{anio}/Timeseries/sst_IOD.png")
          os.system('wget --no-cache -O PronoIOD_APEC.png ' + link_prono_iod)

# ---------------------------------------------------------------------------- #
meses = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D',
         'J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
# lo de arriba es para no tener problemas con el cambio de año

cumes = datetime.now().month
anio = datetime.now().year

if cumes == 12:
     anio +=1


try:
     season = ''.join(meses[cumes:cumes+6])
     Download(season, anio, descarga='Flechita')
except:
     season = ''.join(meses[cumes-1:cumes-1+6])
     Download(season, anio, descarga='Flechita')

descargas = ['ENSO','ENSO-Plume', 'IOD']

for d in  ['ENSO', 'ENSO-Plume', 'IOD']:
     try:
          season = ''.join(meses[cumes:cumes+6])
          Download(season, anio, d)
     except:
          season = ''.join(meses[cumes-1:cumes-1+6])
          Download(season, anio)
        

# ---------------------------------------------------------------------------- #
print('# ------------------------------------------------------------------- #')
print('apec_download.py DONE')
print('# ------------------------------------------------------------------- #')
# ---------------------------------------------------------------------------- #

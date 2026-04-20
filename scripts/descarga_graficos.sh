#!/bin/sh

rm ./*.gif
rm ./*.jpg
rm ./*.pdf
rm ./*.png

# que conda hay?
ANACONDA_DIR="$HOME/anaconda3"
MINICONDA_DIR="$HOME/miniconda3"
# anaconda o miniconda
if [ -d "$ANACONDA_DIR" ]; then
    source "$ANACONDA_DIR/etc/profile.d/conda.sh"
    CONDA_FOUND=true
elif [ -d "$MINICONDA_DIR" ]; then
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    CONDA_FOUND=true
else
    echo "Ni Anaconda3 ni Miniconda3 encontrados. No se puede crear el entorno."
    exit 1
fi

conda activate py_clima



# Ruta a los scrips para correr en python
# Hay que correr esto desde la carpeta raiz del repositorio, 
enlace=./scripts/

python $enlace"text.py"

anio=$(date -d "$date" +"%Y")
mes1=$(date -d "$date -3 month" +"%m")
anio1=$(date -d "$date -3 month" +"%Y")
mes2=$(date -d "$date -2 month" +"%m")
anio2=$(date -d "$date -2 month" +"%Y")
mes3=$(date -d "$date -1 month" +"%m")
anio3=$(date -d "$date -1 month" +"%Y")

# ultimo día del mes. Mes 3 es el anterior.
dfm1=$(cal $(date -d "$date -3 month" +"%m %Y") | awk 'NF {DAYS = $NF}; END {print DAYS}')
dfm2=$(cal $(date -d "$date -2 month" +"%m %Y") | awk 'NF {DAYS = $NF}; END {print DAYS}')
dfm3=$(cal $(date -d "$date -1 month" +"%m %Y") | awk 'NF {DAYS = $NF}; END {print DAYS}')

#current month
cumes=$(date -d "$date" +"%m")

#next month
nxtmes=$(date -d "$date +1 month" +"%m")
#next year
nxtanio=$(date -d "$date +1 month" +"%Y")

# De https://stackoverflow.com/questions/36757864/how-to-get-the-latest-date-for-a-specific-day-of-the-week-in-bash
# requires bash 4.x and GNU date
last_kday() {
  local kday=$1
  local -A numbers=([sunday]=0   [monday]=1 [tuesday]=2 [wednesday]=3
                    [thursday]=4 [friday]=5 [saturday]=6)
  if [[ $kday == *day ]]; then
    kday=${numbers[${kday,,}]}
  elif [[ $kday != [0-6] ]]; then
    echo >&2 "Usage: last_kday weekday"
    return 1
  fi

  local today=$(date +%w)
  local days_ago=$(( today - kday ))
  if (( days_ago < 0 )); then let days_ago+=7; fi
  date -d "$days_ago days ago" +%d
}

### Descarga de imágenes

#Imagen Sectores Niño 
wget -O nino_regions.jpg http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ninoareas_c.jpg

#Imagen Series Niño Sectores 20 años 
wget -O NINO_20.gif http://www.cpc.ncep.noaa.gov/products/CDB/Tropics/figt5.gif

#Status ENSO de CPC
# Sale de https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc_Sp.shtml
cutycapt --url=https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc_Sp.shtml --out=ENSOstatusCPC.png --min-width=1200
convert ENSOstatusCPC.png -crop 580x290+380+150 ENSOstatusCPC.png

# Descarga gráficos APEC Climate Center
python $enlace"apec_download.py"

#Imagen Series Niño Sectores 1 año
wget -O NINO_1.gif http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure02.gif

#Imagen SOI 
wget -O SOI.gif http://www.cpc.ncep.noaa.gov/products/CDB/Tropics/figt1.gif

#Regiones SOI
wget -U "Mozzila" -O SOI_regiones.png https://www.bom.gov.au/climate/enso/indices/images/map-indices.png

#Imagen SOI zoom 
wget -U "Mozzila" -O SOI_zoom.png http://www.bom.gov.au/clim_data/IDCKGSM000/soi30.png

#Imagen MEI
wget -O MEI.png https://www.esrl.noaa.gov/psd/enso/mei/img/mei_lifecycle_current.png

#Imagen RONI -BOM
wget -U "Mozzila" -O ROI.png https://www.bom.gov.au/clim_data/IDCK000072/rnino_3.4.png

#Imagen TSM y Anomalía TSM mensual
wget -O TSM_M1.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes1$anio1/Tropics/figt18.gif
wget -O TSM_M2.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes2$anio2/Tropics/figt18.gif
wget -O TSM_M3.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes3$anio3/Tropics/figt18.gif

#Imagen Anomalía TSM mensual más actual
wget http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/lanina/enso_evolution-status-fcsts-web.pdf
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 7 -- tmp.pdf
#pdftk enso_evolution-status-fcsts-web.pdf cat 7 output tmp.pdf
pdfcrop --margins '-115 -180 -115 -25' tmp.pdf Actual_TSM_Mon.pdf 
convert -density 300 -trim Actual_TSM_Mon.pdf -quality 100 Actual_TSM_Mon.jpg
mv Actual_TSM_Mon-1.jpg Actual_TSM_Mon.jpg
rm Actual_TSM_Mon.pdf

#Imagen TSM sub-superficial
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 12 -- tmp.pdf
pdfcrop --margins '-25 -180 -320 -175' tmp.pdf Actual_TSM_Subsup.pdf
pdfcrop --margins '-425 -145 -17 -30' tmp.pdf TSM_Subsup.pdf
convert -density 300 -trim Actual_TSM_Subsup.pdf -quality 100 Actual_TSM_Subsup.jpg
convert -density 300 -trim TSM_Subsup.pdf -quality 100 TSM_Subsup.jpg
rm Actual_TSM_Subsup.pdf
rm TSM_Subsup.pdf

#Viento zonal en Pac. Ecuatorial
wget -O uv850.gif https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_update/uv850-30d.gif

#Hovmoller TSM
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 15 -- tmp.pdf
pdfcrop --margins '-352 -75 -35 -35' tmp.pdf Hovm.pdf
convert -density 300 -trim Hovm.pdf -quality 100 Hovm.jpg
rm Hovm.pdf

#Imagen IOD 
wget --no-cache -U "Mozilla" -O IOD.png http://www.bom.gov.au/clim_data/IDCK000072/iod1.png

#Imagen OLR y Anomalía OLR mensual
wget -O OLR_M1.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes1$anio1/Tropics/figt25.gif
wget -O OLR_M2.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes2$anio2/Tropics/figt25.gif
wget -O OLR_M3.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes3$anio3/Tropics/figt25.gif

#Generamos flujos de Plumb (con anomalía de función corriente)
python $enlace"calculo_waf.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3"
mv psi_plumb_01$mes1$anio1-${dfm3}$mes3$anio3.png Plumb_Trim.png
python $enlace"calculo_waf.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1"
mv psi_plumb_01$mes1$anio1-${dfm1}$mes1$anio1.png Plumb_M1.png
python $enlace"calculo_waf.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2"
mv psi_plumb_01$mes2$anio2-${dfm2}$mes2$anio2.png Plumb_M2.png
python $enlace"calculo_waf.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3"
mv psi_plumb_01$mes3$anio3-${dfm3}$mes3$anio3.png Plumb_M3.png

# Temperatura SSA -> Descargar desde https://www.crc-sas.org/es/monitoreo_estadisticos.php
# Necesitamos anomalía mensual (Temp_SSA_M3.png) y trimestral (Temp_SSA_Trim.png)

# Precipitación SSA -> Descargar desde https://www.crc-sas.org/es/monitoreo_estadisticos.php
# Necesitamos anomalía mensual (Precip_SSA_M3.png) y trimestral (Precip_SSA_Trim.png)

#Generamos flujos de Plumb (con anomalía de geopotencial 200hPa)
echo "==============================PROBANDO NUEVO CODIGO ============================="
python $enlace"calculo_waf_z200_ncep_gdas.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3"
mv Z_plumb_01$mes1$anio1-${dfm3}$mes3$anio3.png Z_Plumb_Trim.png
python $enlace"calculo_waf_z200_ncep_gdas.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1"
mv Z_plumb_01$mes1$anio1-${dfm1}$mes1$anio1.png Z_Plumb_M1.png
python $enlace"calculo_waf_z200_ncep_gdas.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2"
mv Z_plumb_01$mes2$anio2-${dfm2}$mes2$anio2.png Z_Plumb_M2.png
python $enlace"calculo_waf_z200_ncep_gdas.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3"
mv Z_plumb_01$mes3$anio3-${dfm3}$mes3$anio3.png Z_Plumb_M3.png

#anomalia geop 1000 hPa
python $enlace"anom_var_ncep_gdas.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "1000mb" --latmin "-80" --latmax "0" --lonmin "0" --lonmax "359" --levcont "90" --levint "20" 
mv Anomhgt_1000mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-80_0_0_359.jpg zg1000_M3.jpg 

echo "===========FIN============"
#Imagen Anomalía Z500 mensual
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30"  
mv Anomhgt_500mb_01${mes1}${anio1}_${dfm1}${mes1}${anio1}_-20.jpg zg500_M1.jpg
python $enlace"anom_var_stereo.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30" 
mv Anomhgt_500mb_01${mes2}${anio2}_${dfm2}${mes2}${anio2}_-20.jpg zg500_M2.jpg 
python $enlace"anom_var_stereo.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30"  
mv Anomhgt_500mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-20.jpg zg500_M3.jpg

#Persistencia Anomalías geopotencial
wget -O persis_AnomZ500_M3.gif https://www.cpc.ncep.noaa.gov/products/CDB/Extratropics/fige17.gif

#Imagen Prono ENSO 
#Mes anterior
wget -O PronoENSO_Anterior.png https://iri.columbia.edu/wp-content/uploads/$anio3/$mes3/figure1.png
#Mes actual
wget -O PronoENSO.png https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure07.gif

#Imagen Pluma ENSO (Mes actual puede no estar según en qué fecha se haga la presentación)
#Mes actual
wget -O Pluma_PronoENSO_MesActual.png https://ensoforecast.iri.columbia.edu/cgi-bin/sst_table_img?month=$mes1'&'year=$nxtanio #va con el mes anterior al cumes
#Mes anterior
wget -O Pluma_PronoENSO_MesAnterior.png https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure06.gif

#Imagen Prono IOD 
# el prono de pluma se corre los sabados, la figura de barras se actualiza los martes
# el codigo descarga las dos, probando si el ultimo sabado y martes funciona sino va a la semana anterior
martes=$(last_kday tuesday)
sabado=$(last_kday saturday)
miercoles=$(last_kday wednesday)
python $enlace"prono_IOD_bom.py" --x "${sabado}"

##########################################################################
#Descarga pronosticos NMME, IRI, DIVAR

mes_nmme=$(python $enlace"pronos_update.py" --x "nmme_month_ic")
mes1_nmme=$(python $enlace"pronos_update.py" --x "nmme_month_1")
mes3_nmme=$(python $enlace"pronos_update.py" --x "nmme_month_3")
mes_iri=$(python $enlace"pronos_update.py" --x "iri_month_ic")
season_iri_divar=$(python $enlace"pronos_update.py" --x "season")
season_iri_divar_en=$(python $enlace"pronos_update.py" --x "season_en")
mes_divar=$(python $enlace"pronos_update.py" --x "divar_month_ic")
anio_i=$(python $enlace"pronos_update.py" --x "anio_i")
anio_i_nmme=$(python $enlace"pronos_update.py" --x "anio_i_nmme")
anio_f=$(python $enlace"pronos_update.py" --x "anio_f")
anio_i_abrev=`expr $anio_i - 2000`
anio_f_abrev=`expr $anio_f - 2000`

#Imagen Prono Precip NMME
wget -O Prono_Precip_NMME.png http://www.cpc.ncep.noaa.gov/products/international/nmme/probabilistic_seasonal/samerica_nmme_prec_3catprb_${mes_nmme}IC_${mes1_nmme}${anio_i_nmme}-${mes3_nmme}${anio_f}.png

#Imagen Prono Temp NMME
wget -O Prono_Temp_NMME.png http://www.cpc.ncep.noaa.gov/products/international/nmme/probabilistic_seasonal/samerica_nmme_tmp2m_3catprb_${mes_nmme}IC_${mes1_nmme}${anio_i_nmme}-${mes3_nmme}${anio_f}.png

#Imagen Prono Precip IRI
wget -O Prono_Precip_IRI.gif https://iri.columbia.edu/climate/forecast/net_asmt_nmme/$anio_i/${mes_iri}${anio_i}/images/${season_iri_divar_en}${anio_f_abrev}_SAm_pcp.gif
 
#Imagen Prono Temp IRI
wget -O Prono_Temp_IRI.gif https://iri.columbia.edu/climate/forecast/net_asmt_nmme/$anio/${mes_iri}${anio_i}/images/${season_iri_divar_en}${anio_f_abrev}_SAm_tmp.gif

#Imagen Prono Precip DIVAR
wget --tries=1 -O Prono_Precip_DIVAR.png http://climar.cima.fcen.uba.ar/grafEstacional/for_prec_${season_iri_divar_en}_ic_${mes_divar}_${anio_i}_wsereg_mean_cor.png
 
#Imagen Prono Temp DIVAR
wget --tries=1 -O Prono_Temp_DIVAR.png http://climar.cima.fcen.uba.ar/grafEstacional/for_tref_${season_iri_divar_en}_ic_${mes_divar}_${anio_i}_wsereg_mean_cor.png

###########################################################################
#Descarga pronosticos Copernicus

Temp_URL="https://charts.ecmwf.int/opencharts-api/v1/products/c3s_seasonal_spatial_mm_2mtm_3m/?base_time=${anio}-${cumes}-01T00%3A00%3A00Z&valid_time=${anio}-${nxtmes}-01T00%3A00%3A00Z&area=area13"
IMAGE_Temp_URL=$(wget -qO- "$Temp_URL" | jq -r '.data.link.href')
wget -O "Prono_Temp_copernicus.png" "$IMAGE_Temp_URL"

Precip_URL="https://charts.ecmwf.int/opencharts-api/v1/products/c3s_seasonal_spatial_mm_rain_3m/?base_time=${anio}-${cumes}-01T00%3A00%3A00Z&valid_time=${anio}-${nxtmes}-01T00%3A00%3A00Z&area=area13"
IMAGE_Precip_URL=$(wget -qO- "$Precip_URL" | jq -r '.data.link.href')
wget -O "Prono_Precip_copernicus.png" "$IMAGE_Precip_URL"

rm tmp.pdf enso_evolution-status-fcsts-web.pdf

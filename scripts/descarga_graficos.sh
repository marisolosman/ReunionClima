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

echo "-----------------------------------------------------------"
echo "-----------------------------------------------------------"
echo "En caso de no funcionar la descarga tradicional para los" 
echo "pronosticos de copernicus, ¿Desea usar SELENIUM en python? (si/no):"
read respuesta


python $enlace"apec_download.py"


# Compara la respuesta
if [ "$respuesta" = "si" ]; then
    use_selenium=true
else
    use_selenium=false
fi
use_selenium = false

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

# Prono IOD 
martes=$(last_kday tuesday)
sabado=$(last_kday saturday)
miercoles=$(last_kday wednesday)

#Imagen SOI (fija)
wget -O SOI.gif http://www.cpc.ncep.noaa.gov/products/CDB/Tropics/figt1.gif

#Imagen SOI zoom (fija) # parece que cambio el link enero 2024. Pendiente corroborar que funcione
#siempre el nuevo
#wget -U "Mozzila" -O SOI_zoom.png http://www.bom.gov.au/climate/enso/monitoring/soi30.png
wget -U "Mozzila" -O SOI_zoom.png http://www.bom.gov.au/clim_data/IDCKGSM000/soi30.png

#Regiones SOI (fija)
wget -O SOI_regiones.png https://www.climate.gov/sites/default/files/styles/inline_all/public/Fig1_ENSOindices_SOI_610.png

#Imagen Series Niño Sectores 20 años (fija)
wget -O NINO_20.gif http://www.cpc.ncep.noaa.gov/products/CDB/Tropics/figt5.gif

#Imagen Sectores Niño (fija)
wget -O nino_regions.jpg http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ninoareas_c.jpg

#Imagen Series Niño Sectores 1 año (fija)
wget -O NINO_1.gif http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure02.gif

#Imagen TSM y Anomalía TSM mensual (fija)
wget -O TSM_M1.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes1$anio1/Tropics/figt18.gif
wget -O TSM_M2.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes2$anio2/Tropics/figt18.gif
wget -O TSM_M3.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes3$anio3/Tropics/figt18.gif

#Imagen RONI BOM (fija)
wget -O RONI.png https://www.bom.gov.au/clim_data/IDCK000072/rnino_3.4.png

#Imagen Anomalía TSM mensual más actual (fija)
wget http://www.cpc.ncep.noaa.gov/products/analysis_monitoring/lanina/enso_evolution-status-fcsts-web.pdf
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 7 -- tmp.pdf
#pdftk enso_evolution-status-fcsts-web.pdf cat 7 output tmp.pdf
pdfcrop --margins '-115 -180 -115 -25' tmp.pdf Actual_TSM_Mon.pdf 
convert -density 300 -trim Actual_TSM_Mon.pdf -quality 100 Actual_TSM_Mon.jpg
mv Actual_TSM_Mon-1.jpg Actual_TSM_Mon.jpg
rm Actual_TSM_Mon.pdf

#Imagen TSM sub-superficial (fija)
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 12 -- tmp.pdf
pdfcrop --margins '-25 -180 -320 -175' tmp.pdf Actual_TSM_Subsup.pdf
pdfcrop --margins '-425 -145 -17 -30' tmp.pdf TSM_Subsup.pdf

convert -density 300 -trim Actual_TSM_Subsup.pdf -quality 100 Actual_TSM_Subsup.jpg
convert -density 300 -trim TSM_Subsup.pdf -quality 100 TSM_Subsup.jpg
rm Actual_TSM_Subsup.pdf
rm TSM_Subsup.pdf

#Hovmoller TSM (fija)
qpdf enso_evolution-status-fcsts-web.pdf --pages enso_evolution-status-fcsts-web.pdf 15 -- tmp.pdf
pdfcrop --margins '-352 -75 -35 -35' tmp.pdf Hovm.pdf
convert -density 300 -trim Hovm.pdf -quality 100 Hovm.jpg
rm Hovm.pdf

#Viento zonal en Pac. Ecuatorial (fija)
wget -O uv850.gif https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_update/uv850-30d.gif

#Imagen OLR y Anomalía OLR mensual (fija)
wget -O OLR_M1.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes1$anio1/Tropics/figt25.gif
wget -O OLR_M2.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes2$anio2/Tropics/figt25.gif
wget -O OLR_M3.gif http://www.cpc.ncep.noaa.gov/products/CDB/CDB_Archive_html/bulletin_$mes3$anio3/Tropics/figt25.gif

#Imagen IOD (fija) NO ESTÁ FUNCIONANDO BIEN
wget --no-cache -U "Mozilla" -O IOD.png http://www.bom.gov.au/clim_data/IDCK000072/iod1.png
# http://www.bom.gov.au/climate/enso/monitoring/iod1.png
# en febrero 2024 http://www.bom.gov.au/clim_data/IDCK000072/iod1.png
# El otro link sigue andando pero tiene un grafico viejo

#Flujos de Plumb  (fija)
python $enlace"calculo_waf.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3"
mv psi_plumb_01$mes1$anio1-${dfm3}$mes3$anio3.png Plumb_Trim.png

python $enlace"calculo_waf.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1"
mv psi_plumb_01$mes1$anio1-${dfm1}$mes1$anio1.png Plumb_M1.png

python $enlace"calculo_waf.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2"
mv psi_plumb_01$mes2$anio2-${dfm2}$mes2$anio2.png Plumb_M2.png

python $enlace"calculo_waf.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3"
mv psi_plumb_01$mes3$anio3-${dfm3}$mes3$anio3.png Plumb_M3.png

###########################################################################################################
# "NUEVO" Octubre 2023: Flujos de Plumb con Z200 (fija)
###########################################################################################################
python $enlace"calculo_waf_z200.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3"
mv Z_plumb_01$mes1$anio1-${dfm3}$mes3$anio3.png Z_Plumb_Trim.png

python $enlace"calculo_waf_z200.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1"
mv Z_plumb_01$mes1$anio1-${dfm1}$mes1$anio1.png Z_Plumb_M1.png

python $enlace"calculo_waf_z200.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2"
mv Z_plumb_01$mes2$anio2-${dfm2}$mes2$anio2.png Z_Plumb_M2.png

python $enlace"calculo_waf_z200.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3"
mv Z_plumb_01$mes3$anio3-${dfm3}$mes3$anio3.png Z_Plumb_M3.png
###########################################################################################################
###########################################################################################################
###########################################################################################################

#Imagen Anomalía Z500 yZ30 trimestral (fija)
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30" 
mv Anomhgt_500mb_01${mes1}${anio1}_${dfm3}${mes3}${anio3}_-20.jpg zg500_Trim.jpg
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "30mb" --latr "-20" --levcont "300" --levint "50"  
mv Anomhgt_30mb_01${mes1}${anio1}_${dfm3}${mes3}${anio3}_-20.jpg zg30_Trim.jpg

#Persistencia Anomalías geopotencial (fija)
wget -O persis_AnomZ500_M3.gif https://www.cpc.ncep.noaa.gov/products/CDB/Extratropics/fige17.gif

#Vórtice polar (fija)
wget -O vorticeHS.gif https://www.cpc.ncep.noaa.gov/products/CDB/Extratropics/figs8.gif

#anomalia mensual pp smn (fija)
wget --user-agent='Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' -O Precip_SMN_M3.gif https://estaticos.smn.gob.ar/hidro/imagenes/allu1m.gif

#anomalia mensual temp smn (fija)
wget --user-agent='Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' -O Temp_SMN_M3.gif https://estaticos.smn.gob.ar/clima/imagenes/atmed1.gif 

#Imagen Anomalía Z500 mensual (fija)
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30"  
mv Anomhgt_500mb_01${mes1}${anio1}_${dfm1}${mes1}${anio1}_-20.jpg zg500_M1.jpg

python $enlace"anom_var_stereo.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30" 
mv Anomhgt_500mb_01${mes2}${anio2}_${dfm2}${mes2}${anio2}_-20.jpg zg500_M2.jpg 

python $enlace"anom_var_stereo.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "500mb" --latr "-20" --levcont "120" --levint "30"  
mv Anomhgt_500mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-20.jpg zg500_M3.jpg

#Imagen Anomalía Z30 mensual (fija)
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1" --variable "Zg" --level "30mb" --latr "-20" --levcont "600" --levint "50"   
mv Anomhgt_30mb_01${mes1}${anio1}_${dfm1}${mes1}${anio1}_-20.jpg zg30_M1.jpg

python $enlace"anom_var_stereo.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2" --variable "Zg" --level "30mb" --latr "-20" --levcont "600" --levint "50"  
mv Anomhgt_30mb_01${mes2}${anio2}_${dfm2}${mes2}${anio2}_-20.jpg zg30_M2.jpg 

python $enlace"anom_var_stereo.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "30mb" --latr "-20" --levcont "600" --levint "50"   
mv Anomhgt_30mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-20.jpg zg30_M3.jpg

#Imagen Anomalía T30 mensual (fija)
python $enlace"anom_var_stereo.py" --dateinit "$anio1-$mes1-01" --dateend "$anio1-$mes1-$dfm1" --variable "T" --level "30mb" --latr "-20" --levcont "25" --levint "2"   
mv Anomair_30mb_01${mes1}${anio1}_${dfm1}${mes1}${anio1}_-20.jpg T30_M1.jpg

python $enlace"anom_var_stereo.py" --dateinit "$anio2-$mes2-01" --dateend "$anio2-$mes2-$dfm2" --variable "T" --level "30mb" --latr "-20" --levcont "25" --levint "2"  
mv Anomair_30mb_01${mes2}${anio2}_${dfm2}${mes2}${anio2}_-20.jpg T30_M2.jpg 

python $enlace"anom_var_stereo.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "T" --level "30mb" --latr "-20" --levcont "25" --levint "2"   
mv Anomair_30mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-20.jpg T30_M3.jpg

#anomalia mensual Temp smn (fija)
wget --user-agent='Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' -O Temp_SMN_M3.gif https://estaticos.smn.gob.ar/clima/imagenes/atmed1.gif

#anomalia geop 1000 hPa (fija)
python $enlace"anom_var.py" --dateinit "$anio3-$mes3-01" --dateend "$anio3-$mes3-$dfm3" --variable "Zg" --level "1000mb" --latmin "-80" --latmax "0" --lonmin "0" --lonmax "359" --levcont "90" --levint "20" 
mv Anomhgt_1000mb_01${mes3}${anio3}_${dfm3}${mes3}${anio3}_-80_0_0_359.jpg zg1000_M3.jpg 

#anomalia trimestral smn (fija)
wget --user-agent='Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' -O Precip_SMN_Trim.gif https://estaticos.smn.gob.ar/hidro/imagenes/allu3m.gif

#anomalia trimestral smn (fija)
wget --user-agent='Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' -O Temp_SMN_Trim.gif https://estaticos.smn.gob.ar/clima/imagenes/atmed3.gif

#anomalia mensual SSA (fija)
wget --no-check-certificate -O Temp_SSA_M3.gif https://www.crc-sas.org/es/clima/imagenes/Ratmed1.gif

#anomalia trimestral SSA (fija)
wget --no-check-certificate -O Temp_SSA_Trim.gif https://www.crc-sas.org/es/clima/imagenes/Ratmed3.gif

#Monitoreo Agujero Ozono (Fija)
wget -O Ozono_CPC.png http://www.cpc.ncep.noaa.gov/products/stratosphere/polar/gif_files/ozone_hole_plot.png
wget -O Ozono_Copernicus.png https://sites.ecmwf.int/data/cams/plots/ozone/cams_sh_ozone_area_$anio.png
wget -O TempMinAnt_Copernicus.png https://sites.ecmwf.int/data/cams/plots/ozone/cams_sh_50hPa_temperature_minimum_$anio.png

#Monitoreo Agujero Ozono (¡¡¡Cambiar!!!)
wget -O Ozono_sounding.png https://www.esrl.noaa.gov/gmd/webdata/ozwv/ozsNDJes/spo/iadv/SPO_$anio-15-12.21.png

#Monitoreo Estratósfera (Fija)
wget -O AnomT_SH_tvsp_2002.png https://www.cpc.ncep.noaa.gov/products/stratosphere/strat-trop/gif_files/time_pres_TEMP_ANOM_ALL_SH_2002.gif
wget -O AnomU_SH_tvsp_2002.png https://www.cpc.ncep.noaa.gov/products/stratosphere/strat-trop/gif_files/time_pres_UGRD_ANOM_ALL_SH_2002.gif
wget -O AnomT_SH_tvsp.png https://www.cpc.ncep.noaa.gov/products/stratosphere/strat-trop/gif_files/time_pres_TEMP_ANOM_ALL_SH_$anio.png
wget -O AnomU_SH_tvsp.png https://www.cpc.ncep.noaa.gov/products/stratosphere/strat-trop/gif_files/time_pres_UGRD_ANOM_ALL_SH_$anio.png

#Monitoreo Estratósfera (Fija)
wget -O vt_4575.pdf https://acd-ext.gsfc.nasa.gov/Data_services/met/metdata/annual/merra2/flux/vt45_75-45s_50_${anio}_merra2.pdf
convert -density 300 -trim vt_4575.pdf -quality 100 vt_4575.jpg
wget -O u_60.pdf https://acd-ext.gsfc.nasa.gov/Data_services/met/metdata/annual/merra2/wind/u60s_10_${anio}_merra2.pdf
convert -density 300 -trim u_60.pdf -quality 100 u_60.jpg

#Monitoreo Estratósfera - Extensión Vórtice (Fija)
wget -O ext_vortice.png https://www.cpc.ncep.noaa.gov/products/stratosphere/polar/gif_files/vtx_sh.png

#Imagen MEI (fija)
wget -O MEI.png https://www.esrl.noaa.gov/psd/enso/mei/img/mei_lifecycle_current.png

#Imagen Prono ENSO (fija)
wget -O PronoENSO_Anterior.png https://iri.columbia.edu/wp-content/uploads/$anio3/$mes3/figure1.png

# A partir de Junio el modelo de link es este:
#https://iri.columbia.edu/wp-content/uploads/2024/06/CPCoff_ENSOprobs_062024.png pero es el prono de mayo... 
wget -O PronoENSO.png https://iri.columbia.edu/wp-content/uploads/$anio/$cumes/figure1.png #CPCoff_ENSOprobs_$cumes$anio.png

#Imagen Pluma ENSO (Mes actual puede no estar según en qué fecha se haga la presentación)

# VAN CAMBIANDO LOS LINK SIN MOTIVO!
# PARA Abril 2023 funciona asi:
#wget -O Pluma_PronoENSO_MesActual.png https://ensoforecast.iri.columbia.edu/cgi-bin/sst_table_img?month=$cumes'&'year=$nxtanio
wget -O Pluma_PronoENSO_MesActual.png https://ensoforecast.iri.columbia.edu/cgi-bin/sst_table_img?month=$mes1'&'year=$anio1 

#va con el mes anterior al cumes
wget -O Pluma_PronoENSO_MesAnterior.png https://ensoforecast.iri.columbia.edu/cgi-bin/sst_table_img?month=$mes2'&'year=$anio2


#Imagen Prono IOD (fija)
## PROBANDO ##
# el prono de pluma se corre los sabados, la figura de barras se actualiza los martes
# el codigo descarga las dos, probando si el ultimo sabado y martes funciona sino va a la semana anterior
python $enlace"prono_IOD_bom.py" --x "${sabado}"

#wget --no-cache -U "Mozilla" -O PronoIOD.png http://www.bom.gov.au/climate/enso/wrap-up/archive/${anio}${cumes}${martes}.sstOutlooks_iod.png
#wget --no-cache -U "Mozilla" -O PronoIOD_NextMon.png http://www.bom.gov.au/climate/model-summary/archive/${anio}${cumes}${martes}.iod_summary_2.png
#wget --no-cache -U "Mozilla" -O PronoIOD_NextMon.png http://www.bom.gov.au/climate/model-summary/archive/${anio}${cumes}${miercoles}.iod_summary_2.png
#wget --no-cache -U "Mozilla" -O PronoIOD_NextOtMon.png http://www.bom.gov.au/climate/model-summary/archive/${anio}${cumes}${martes}.iod_summary_3.png
#wget -O PronoIOD_APEC.png https://www.apcc21.org/apcc_images/NEW/GLOBE/ENSO/$anio/$nxtmes/Timeseries/sst_IOD.png


##########################################################################

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

###########################################################################
#Imagen Prono Precip NMME (¡¡¡Cambiar!!!)---> probando=FIJA
wget -O Prono_Precip_NMME.png http://www.cpc.ncep.noaa.gov/products/international/nmme/probabilistic_seasonal/samerica_nmme_prec_3catprb_${mes_nmme}IC_${mes1_nmme}${anio_i_nmme}-${mes3_nmme}${anio_f}.png

#Imagen Prono Temp NMME (¡¡¡Cambiar!!!)---> probando=FIJA
wget -O Prono_Temp_NMME.png http://www.cpc.ncep.noaa.gov/products/international/nmme/probabilistic_seasonal/samerica_nmme_tmp2m_3catprb_${mes_nmme}IC_${mes1_nmme}${anio_i_nmme}-${mes3_nmme}${anio_f}.png

#Imagen Prono Precip IRI (¡¡¡Cambiar!!!)---> probando=FIJA
wget -O Prono_Precip_IRI.gif https://iri.columbia.edu/climate/forecast/net_asmt_nmme/$anio_i/${mes_iri}${anio_i}/images/${season_iri_divar_en}${anio_f_abrev}_SAm_pcp.gif
 
#Imagen Prono Temp IRI (¡¡¡Cambiar!!!)---> probando=FIJA
wget -O Prono_Temp_IRI.gif https://iri.columbia.edu/climate/forecast/net_asmt_nmme/$anio/${mes_iri}${anio_i}/images/${season_iri_divar_en}${anio_f_abrev}_SAm_tmp.gif

#Imagen Prono DIVAR (¡¡¡Cambiar!!!)---> probando=FIJA
wget --tries=1 -O Prono_Precip_DIVAR.png http://climar.cima.fcen.uba.ar/grafEstacional/for_prec_${season_iri_divar_en}_ic_${mes_divar}_${anio_i}_wsereg_mean_cor.png
 
#Imagen Prono DIVAR (¡¡¡Cambiar!!!)---> probando=FIJA
wget --tries=1 -O Prono_Temp_DIVAR.png http://climar.cima.fcen.uba.ar/grafEstacional/for_tref_${season_iri_divar_en}_ic_${mes_divar}_${anio_i}_wsereg_mean_cor.png

# TEST DESCARGA AUTOMATICA COPERNICUS
python $enlace"test_download_copernicus_forecast.py" --mes "$cumes" --anio "$anio" --nxtanio "$nxtanio" --use_selenium "$use_selenium"

#prono copernicus (Cambiar)
#wget --no-cache -O Prono_Temp_copernicus.png https://charts.ecmwf.int/streaming/20231117-0930/22/ps2png-worker-commands-76898cbbf-xfdn2-6fe5cac1a363ec1525f54343b6cc9fd8-vtBICf.png

#prono copernicus (Cambiar)
#wget --no-cache -O Prono_Precip_copernicus.png https://charts.ecmwf.int/streaming/20231116-2230/2c/ps2png-worker-commands-76898cbbf-rqq8t-6fe5cac1a363ec1525f54343b6cc9fd8-W1Ygyc.png

# Flechita de ENSO (No es automático)
# Sale de http://www.bom.gov.au/climate/enso/outlook/
#cutycapt --url=http://www.bom.gov.au/climate/enso/outlook/ --out=enso_flechita.png --min-width=1200
#convert enso_flechita.png -crop 240x159+323+316 enso_flechita.png
wget -O enso_flechita.png -U 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' http://www.bom.gov.au/climate/enso/outlook/images/cg/el-nino.png

#Status ENSO de CPC
# Sale de https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc_Sp.shtml
cutycapt --url=https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc_Sp.shtml --out=ENSOstatusCPC.png --min-width=1200
convert ENSOstatusCPC.png -crop 580x260+380+150 ENSOstatusCPC.png

# Flechita de ENSO (APEC Climate Center)
#wget -O enso_flechita_apec.png https://www.apcc21.org/apcc_images/NEW/GLOBE/ENSO/$nxtanio/$nxtmes/Alert/ENSO_Alert.png

rm tmp.pdf enso_evolution-status-fcsts-web.pdf




#!/usr/bin/env python3
"""
Genera comunas-chile.csv (comuna,region,prioridad) cubriendo Chile salvo el Gran Santiago.
Prioridad 1 = mayor población/comercio. El orquestador procesa la cola por prioridad ascendente.
Reproducible: editar las listas y re-correr.
"""
import csv
from pathlib import Path
OUT = Path(__file__).parent / "comunas-chile.csv"

# 34 comunas del Gran Santiago ya scrapeadas -> se excluyen
SANTIAGO = {"Santiago","Providencia","Ñuñoa","Las Condes","Vitacura","Lo Barnechea","La Reina",
 "Macul","Peñalolén","La Florida","Puente Alto","San Joaquín","San Miguel","San Bernardo",
 "La Cisterna","El Bosque","La Granja","La Pintana","San Ramón","Pedro Aguirre Cerda","Lo Espejo",
 "Cerrillos","Maipú","Estación Central","Quinta Normal","Lo Prado","Pudahuel","Cerro Navia",
 "Renca","Quilicura","Huechuraba","Recoleta","Independencia","Conchalí"}

# (prioridad, region, [comunas])  -- norte a sur
GROUPS = [
 # P1: las 3 grandes conurbaciones tras Santiago
 (1,"Biobío",["Concepción","Talcahuano","Hualpén","San Pedro de la Paz","Chiguayante","Penco","Coronel","Lota","Tomé","Hualqui","Santa Juana"]),
 (1,"Valparaíso",["Valparaíso","Viña del Mar","Quilpué","Villa Alemana","Concón"]),
 (1,"Coquimbo",["La Serena","Coquimbo"]),
 # P2: ciudades grandes / capitales regionales
 (2,"Antofagasta",["Antofagasta","Calama"]),
 (2,"Tarapacá",["Iquique","Alto Hospicio"]),
 (2,"Arica y Parinacota",["Arica"]),
 (2,"Atacama",["Copiapó"]),
 (2,"Coquimbo",["Ovalle"]),
 (2,"O'Higgins",["Rancagua","Machalí"]),
 (2,"Maule",["Talca","Curicó","Linares"]),
 (2,"Ñuble",["Chillán","Chillán Viejo"]),
 (2,"Biobío",["Los Ángeles"]),
 (2,"La Araucanía",["Temuco","Padre Las Casas"]),
 (2,"Los Ríos",["Valdivia"]),
 (2,"Los Lagos",["Puerto Montt","Osorno"]),
 (2,"Magallanes",["Punta Arenas"]),
 # P3: ciudades medianas y polos turísticos/comerciales
 (3,"Valparaíso",["San Antonio","Quillota","San Felipe","Los Andes","La Calera","Limache","Casablanca"]),
 (3,"Coquimbo",["Illapel","Vicuña","Andacollo","Los Vilos","Salamanca"]),
 (3,"Antofagasta",["Tocopilla","Mejillones","Taltal"]),
 (3,"Atacama",["Vallenar","Caldera","Chañaral","Diego de Almagro"]),
 (3,"O'Higgins",["San Fernando","Rengo","Santa Cruz","Graneros","San Vicente","Pichilemu"]),
 (3,"Maule",["Molina","Constitución","Cauquenes","San Javier","Parral"]),
 (3,"Ñuble",["San Carlos","Bulnes","Yungay","Quirihue"]),
 (3,"Biobío",["Mulchén","Nacimiento","Cabrero","Arauco","Curanilahue","Lebu","Cañete"]),
 (3,"La Araucanía",["Villarrica","Pucón","Angol","Victoria","Lautaro","Nueva Imperial","Loncoche","Pitrufquén"]),
 (3,"Los Ríos",["La Unión","Río Bueno","Panguipulli","Los Lagos","Mariquina","Paillaco"]),
 (3,"Los Lagos",["Puerto Varas","Castro","Ancud","Quellón","Calbuco","Llanquihue","Frutillar","Purranque"]),
 (3,"Aysén",["Coyhaique","Puerto Aysén"]),
 (3,"Magallanes",["Puerto Natales","Porvenir"]),
 (3,"Tarapacá",["Pozo Almonte","Pica"]),
 (3,"Arica y Parinacota",["Putre","Camarones"]),
 # P4: comunas RM fuera del Gran Santiago + provinciales restantes
 (4,"Metropolitana",["Colina","Lampa","Tiltil","Melipilla","Curacaví","Talagante","Peñaflor","El Monte",
   "Isla de Maipo","Padre Hurtado","Buin","Paine","Calera de Tango","Pirque","San José de Maipo",
   "María Pinto","Alhué","San Pedro","Padre Hurtado"]),
 (4,"Valparaíso",["Olmué","Cartagena","El Quisco","Algarrobo","El Tabo","Santo Domingo","La Ligua","Cabildo",
   "Zapallar","Papudo","Puchuncaví","Nogales","Hijuelas","La Cruz","Calle Larga","San Esteban","Putaendo","Llaillay","Catemu"]),
 (4,"O'Higgins",["Mostazal","Requínoa","Chimbarongo","Doñihue","Las Cabras","Peumo","Coltauco","Codegua","Olivar","Nancagua","Chépica","Lolol","Marchigüe"]),
 (4,"Maule",["Longaví","Río Claro","San Clemente","Teno","Sagrada Familia","Villa Alegre","Colbún","Yerbas Buenas","Pelarco","Pencahue","Hualañé","Licantén"]),
 (4,"Ñuble",["Coelemu","Quillón","Coihueco","San Nicolás","Pinto","El Carmen","Pemuco","Ñiquén","San Fabián"]),
 (4,"Biobío",["Yumbel","Laja","San Rosendo","Los Álamos","Tirúa","Contulmo","Quilleco","Santa Bárbara","Negrete","Tucapel","Antuco","Mininco","Florida"]),
 (4,"La Araucanía",["Carahue","Collipulli","Gorbea","Freire","Cunco","Vilcún","Traiguén","Curacautín","Galvarino","Lonquimay","Renaico","Purén","Los Sauces","Toltén","Teodoro Schmidt"]),
 (4,"Los Ríos",["Futrono","Corral","Máfil","Lago Ranco","Lanco"]),
 (4,"Los Lagos",["Fresia","Fresia","Los Muermos","Maullín","Río Negro","San Pablo","Chonchi","Dalcahue","Quemchi","Quinchao","Puerto Octay","Puyehue","Hualaihué","Cochamó","Chaitén"]),
 (4,"Aysén",["Chile Chico","Cochrane","Puerto Cisnes","Cisnes"]),
 (4,"Magallanes",["Natales"]),
 (4,"Atacama",["Tierra Amarilla","Huasco","Freirina","Alto del Carmen"]),
 (4,"Coquimbo",["Monte Patria","Combarbalá","Punitaqui","Canela","La Higuera","Paihuano","Río Hurtado"]),
 (4,"Antofagasta",["María Elena","San Pedro de Atacama","Sierra Gorda"]),
]

def main():
    seen=set(); rows=[]
    for prio,region,comunas in GROUPS:
        for c in comunas:
            if c in SANTIAGO: continue
            key=(c,region)
            if key in seen: continue
            seen.add(key); rows.append((c,region,prio))
    rows.sort(key=lambda r:(r[2],r[1],r[0]))
    with open(OUT,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["comuna","region","prioridad"]); w.writerows(rows)
    print(f"{len(rows)} comunas -> {OUT.name}")
    from collections import Counter
    for p,k in sorted(Counter(r[2] for r in rows).items()):
        print(f"  prioridad {p}: {k} comunas")

if __name__=="__main__": main()

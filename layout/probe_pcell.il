; Do hinh dang pcell nmos1v/pmos1v va cac via cua gpdk090 (chay batch).
; virtuoso -nograph -restore layout/probe_pcell.il  (trong thu muc co cds.lib)
procedure(probeDumpFigs(cv indent)
  foreach(s cv~>shapes
    printf("%sSHAPE %s %L %L\n" indent s~>objType s~>lpp s~>bBox))
  foreach(t cv~>terminals
    foreach(p t~>pins
      foreach(f p~>figs
        printf("%sPIN %s %L %L\n" indent t~>name f~>lpp f~>bBox)))))

let((tf lib cv sm cdf inst)
  tf = techGetTechFile(ddGetObj("gpdk090"))
  printf("== VIADEFS\n")
  foreach(v tf~>viaDefs
    printf("VIA %s %L %L\n" v~>name v~>layer1Name v~>layer2Name))
  printf("== LAYERS\n")
  foreach(l tf~>layers printf("LAYER %s %L\n" l~>name l~>number))
  foreach(dev list("nmos1v" "pmos1v")
    printf("== CDF %s\n" dev)
    cdf = cdfGetBaseCellCDF(ddGetObj("gpdk090" dev))
    foreach(p cdf~>parameters
      printf("CDFPARAM %s type=%L def=%L\n" p~>name p~>paramType p~>defValue))
    sm = dbOpenCellViewByType("gpdk090" dev "layout")
    printf("== PCELLPARAMS %s\n" dev)
    foreach(p sm~>parameters~>value
      printf("PARAM %s %L %L\n" p~>name p~>valueType p~>value)))
  lib = dbCreateLib("PROBE" "./PROBE")
  techBindTechFile(lib "gpdk090")
  cv = dbOpenCellViewByType("PROBE" "t" "layout" "maskLayout" "w")
  foreach(dev list("nmos1v" "pmos1v")
    foreach(w list("120n" "240n" "480n")
      inst = dbCreateParamInstByMasterName(cv "gpdk090" dev "layout" strcat(dev "_" w)
               list(0 0) "R0" 1 list(list("w" "string" w) list("l" "string" "100n")))
      printf("== INST %s w=%s bBox=%L\n" dev w inst~>master~>bBox)
      probeDumpFigs(inst~>master "  ")))
  dbSave(cv) dbClose(cv)
  printf("PROBE_DONE\n"))
exit()

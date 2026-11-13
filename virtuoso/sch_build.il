;; sch_build.il -- reusable SKILL helpers: netlist data -> schematic + symbol views.
;; Called by virtuoso/sch_*.il; runs in
;; `virtuoso -nograph -restore gen.il < /dev/null` inside the project dir (~/ALU_PROJ).
;;   sbBegin()                         reset counters, open pin masters
;;   sbLib(lib techLib)                create OA lib (if missing) and attach techLib
;;   sbCell(lib cell pins insts)       pins  = ((name dir) ...), dir input|output|inputOutput
;;                                     insts = ((name masterLib masterCell ((term net) ...)
;;                                               ((cdfParam value) ...)) ...)
;;   sbEnd()                           print "SB_SUMMARY ..." and exit (status 0 = no error)
;; Drawing: instances in two rows (pmos* on top, everything else below); every instance
;; terminal gets a short wire stub with a wire label = net name; pins are placed left
;; (input), right (output) and below (inputOutput), each with its own labelled stub.
;; Connectivity is by net name only (no routing). Never name a variable t or nil.

sbStub = 0.25     ; stub length
sbGap  = 1.5      ; space between instances
sbGrid = 0.125

procedure(sbSnap(v) sbGrid * round(v / sbGrid))

procedure(sbBegin()
  sbErrors = 0
  sbCells = 0
  sbPinMaster = list(nil
    'input dbOpenCellViewByType("basic" "ipin" "symbol" nil "r")
    'output dbOpenCellViewByType("basic" "opin" "symbol" nil "r")
    'inputOutput dbOpenCellViewByType("basic" "iopin" "symbol" nil "r"))
  unless(get(sbPinMaster 'input) && get(sbPinMaster 'output) && get(sbPinMaster 'inputOutput)
    printf("SB_ERROR cannot open basic ipin/opin/iopin symbols (check cds.lib)\n")
    exit(1)))

procedure(sbLib(lib tech)
  let((d)
    d = ddGetObj(lib)
    unless(d
      d = ddCreateLib(lib strcat("./" lib)))
    if(d then
      techSetTechLibName(d tech)
      printf("SB_LIB %s path=%s tech=%L\n" lib d~>readPath techGetTechLibName(d))
    else
      printf("SB_ERROR cannot create library %s\n" lib)
      sbErrors++)
    d))

;; set CDF params like the Edit Properties form: value, then that param's callback
procedure(sbSetParams(inst params)
  let((cdf p)
    when(params
      cdf = cdfGetInstCDF(inst)
      ; PDK callbacks need the form-init data (gpdk090: PasCdfCommitValue)
      cdfgData = cdf
      cdfgForm = nil
      when(cdf~>formInitProc && cdf~>formInitProc != ""
        unless(errset(evalstring(sprintf(nil "%s(cdfgData)" cdf~>formInitProc)))
          printf("SB_WARN formInitProc %L failed: %L\n" cdf~>formInitProc errset.errset)))
      foreach(pv params
        p = get(cdf stringToSymbol(car(pv)))
        if(p then
          p~>value = cadr(pv)
          when(stringp(p~>callback) && p~>callback != ""
            cdfgData = cdf
            cdfgForm = nil
            unless(errsetstring(p~>callback)
              printf("SB_WARN %s: callback of %s failed: %L -> %L\n" inst~>name car(pv)
                     p~>callback errset.errset)))
        else
          printf("SB_ERROR %s: no CDF param %s\n" inst~>name car(pv))
          sbErrors++))
      ; what the netlister will see (callbacks may have changed other params)
      printf("SB_PARAMS %s" inst~>name)
      foreach(pv params printf(" %s=%L" car(pv) get(cdf stringToSymbol(car(pv)))~>value))
      foreach(pv params
        unless(get(cdf stringToSymbol(car(pv)))~>value == cadr(pv)
          printf(" MISMATCH(%s)" car(pv))
          sbErrors++))
      printf("\n"))))

;; connection point of terminal `term` (nil = first terminal) of `inst` in cellview coords,
;; and the side it sits on (relative to the box around all pins of the master)
procedure(sbTermPoint(inst term)
  let((master trm pts c xs ys side)
    master = inst~>master
    trm = if(term car(setof(x master~>terminals x~>name == term)) car(master~>terminals))
    unless(trm error("sbTermPoint: %s has no terminal %L" inst~>name term))
    c = centerBox(car(trm~>pins)~>fig~>bBox)
    pts = foreach(mapcar x master~>terminals centerBox(car(x~>pins)~>fig~>bBox))
    xs = mapcar('car pts)      ; not 'xCoord: it is an alias, mapcar cannot call it
    ys = mapcar('cadr pts)
    side = car(car(sort(list(
      list("left"   xCoord(c) - apply('min xs))
      list("right"  apply('max xs) - xCoord(c))
      list("bottom" yCoord(c) - apply('min ys))
      list("top"    apply('max ys) - yCoord(c)))
      lambda((a b) cadr(a) < cadr(b)))))
    list(dbTransformPoint(c inst~>transform) side)))   ; all instances are placed R0

procedure(sbWire(cv p side net)
  let((p2 w just)
    p2 = cond(
      (side == "left"   xCoord(p) - sbStub : yCoord(p))
      (side == "right"  xCoord(p) + sbStub : yCoord(p))
      (side == "bottom" xCoord(p) : yCoord(p) - sbStub)
      (side == "top"    xCoord(p) : yCoord(p) + sbStub))
    just = cond((side == "left" "lowerRight") (side == "right" "lowerLeft")
                (side == "bottom" "upperCenter") (side == "top" "lowerCenter"))
    w = car(schCreateWire(cv "draw" "full" list(p p2) 0.0625 0.0625 0.0))
    schCreateWireLabel(cv w p2 net just "R0" "stick" 0.0625 nil)))

procedure(sbPins(cv pins dir side x0 y0 dx dy)
  let((x y pin)
    x = x0
    y = y0
    foreach(p pins
      pin = schCreatePin(cv get(sbPinMaster dir) car(p) cadr(p) nil sbSnap(x):sbSnap(y) "R0")
      sbWire(cv car(sbTermPoint(pin nil)) side car(p))
      x = x + dx
      y = y + dy)))

procedure(sbDraw(cv pins insts)
  let((x y n master inst bb)
    x = list(0.0 0.0)          ; x cursor of row 0 (nmos, subcells) and row 1 (pmos)
    foreach(i insts
      master = dbOpenCellViewByType(cadr(i) caddr(i) "symbol" nil "r")
      unless(master error("no symbol %s/%s" cadr(i) caddr(i)))
      n = if(rexMatchp("^pmos" caddr(i)) 1 0)
      bb = master~>bBox
      y = n * 3.0
      inst = dbCreateInst(cv master car(i) sbSnap(nth(n x) - xCoord(car(bb))):y "R0")
      setcar(nthcdr(n x) sbSnap(nth(n x) + xCoord(cadr(bb)) - xCoord(car(bb)) + sbGap))
      sbSetParams(inst nth(4 i))
      foreach(c nth(3 i)
        n = sbTermPoint(inst car(c))
        sbWire(cv car(n) cadr(n) cadr(c))))
    x = apply('max x)
    sbPins(cv setof(p pins cadr(p) == "input") 'input "right" -3.0 0.0 0.0 -0.75)
    sbPins(cv setof(p pins cadr(p) == "output") 'output "left" x + 1.5 0.0 0.0 -0.75)
    ; VDD/VSS ngay duoi chan vao cuoi cung (y co dinh -3.0 trung chan vao thu 5 khi co bus)
    sbPins(cv setof(p pins cadr(p) == "inputOutput") 'inputOutput "right" -3.0
           -0.75 * (length(setof(p pins cadr(p) == "input")) + 1) 0.0 -0.75)))

procedure(sbCell(lib cell pins insts)
  let((cv res ok)
    sbCells++
    cv = dbOpenCellViewByType(lib cell "schematic" "schematic" "w")   ; "w" replaces old view
    if(!cv then
      printf("SB_ERROR cannot open %s/%s/schematic for write\n" lib cell)
      sbErrors++
    else
      ok = errset(sbDraw(cv pins insts) t)
      unless(ok
        printf("SB_ERROR %s/%s: %L\n" lib cell car(errset.errset))
        sbErrors++)
      res = schCheck(cv)
      printf("SB_CELL %s/%s insts=%d schCheck errors=%L warnings=%L\n"
             lib cell length(insts) car(res) cadr(res))
      unless(car(res) == 0 sbErrors++)
      ; connectivity as extracted by schCheck (second, netlister-independent check)
      foreach(inst cv~>instances
        unless(member(inst~>master~>cellName '("ipin" "opin" "iopin"))
          printf("SB_NET %s %s %s" cell inst~>name inst~>master~>cellName)
          foreach(it inst~>instTerms printf(" %s=%s" it~>name it~>net~>name))
          printf(" w=%L fw=%L l=%L fingers=%L m=%L\n" inst~>w inst~>fw inst~>l inst~>fingers inst~>m)))
      dbSave(cv)
      dbClose(cv)
      when(ok
        unless(errset(sbSymbol(lib cell pins) t)
          printf("SB_ERROR %s/%s symbol: %L\n" lib cell car(errset.errset))
          sbErrors++)))))

;; symbol drawn directly (schViewToView stalls in -nograph): box, inputs left, outputs
;; right, inputOutput on top (VSS/GND at the bottom), pin names inside, [@instanceName] label
procedure(sbSymbol(lib cell pins)
  let((sym ins outs tops bots h w lbl)
    ins = setof(p pins cadr(p) == "input")
    outs = setof(p pins cadr(p) == "output")
    bots = setof(p pins cadr(p) == "inputOutput" && member(car(p) '("VSS" "GND")))
    tops = setof(p pins cadr(p) == "inputOutput" && !member(car(p) '("VSS" "GND")))
    h = 0.25 * (max(length(ins) length(outs)) + 1)
    w = max(1.0 0.25 * (max(length(tops) length(bots)) + 1))
    sym = dbOpenCellViewByType(lib cell "symbol" "schematicSymbol" "w")
    dbCreateRect(sym list("device" "drawing") list(0:0 w:h))
    dbCreateRect(sym list("instance" "drawing") list(-0.25:-0.25 w+0.25:h+0.25))
    dbCreateLabel(sym list("annotate" "drawing8") w/2:h/2 cell "centerCenter" "R0" "stick" 0.0625)
    lbl = dbCreateLabel(sym list("annotate" "drawing7") 0:h+0.0625 "[@instanceName]"
                        "lowerLeft" "R0" "stick" 0.0625)
    lbl~>labelType = "NLPLabel"
    sbSymPins(sym ins 0:h -0.25:0.0 0.0:-0.25 "centerLeft")
    sbSymPins(sym outs w:h 0.25:0.0 0.0:-0.25 "centerRight")
    sbSymPins(sym tops 0:h 0.0:0.25 0.25:0.0 "upperCenter")
    sbSymPins(sym bots 0:0 0.0:-0.25 0.25:0.0 "lowerCenter")
    dbSave(sym)
    printf("SB_SYMBOL %s/%s pins:" lib cell)
    foreach(trm sym~>terminals
      printf(" %s:%s@%L" trm~>name trm~>direction centerBox(car(trm~>pins)~>fig~>bBox)))
    printf("\n")
    dbClose(sym)))

;; pins along one edge: k-th pin sits on the edge at `edge`+(k+1)*step, its stub sticks out by `out`
procedure(sbSymPins(sym pins edge out step just)
  let((k e p net fig)
    k = 1
    foreach(pn pins
      e = xCoord(edge) + k * xCoord(step) : yCoord(edge) + k * yCoord(step)
      p = xCoord(e) + xCoord(out) : yCoord(e) + yCoord(out)
      dbCreateLine(sym list("device" "drawing") list(e p))
      net = dbMakeNet(sym car(pn))
      dbCreateTerm(net car(pn) cadr(pn))
      fig = dbCreateRect(sym list("pin" "drawing")
                         list(xCoord(p) - 0.03125:yCoord(p) - 0.03125 xCoord(p) + 0.03125:yCoord(p) + 0.03125))
      dbCreatePin(net fig car(pn))
      ; pin name just inside the box
      dbCreateLabel(sym list("pin" "annotate")
                    xCoord(e) - xCoord(out) / 2.5 : yCoord(e) - yCoord(out) / 2.5
                    car(pn) just "R0" "stick" 0.05)
      k++)))

procedure(sbEnd()
  printf("SB_SUMMARY cells=%d errors=%d\n" sbCells sbErrors)
  exit(if(sbErrors == 0 0 1)))

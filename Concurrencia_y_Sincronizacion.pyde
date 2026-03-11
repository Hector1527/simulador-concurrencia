import threading
import time
import random

# ============================================================
# SIMULADOR DE CONCURRENCIA Y SINCRONIZACION
# Analogia: Restaurante
# ============================================================
# Teclas para cambiar de modo:
#   1 - Condicion de Carrera
#   2 - Semaforo
#   3 - Mutex + Seccion Critica
#   4 - Deadlock
#   5 - Monitor
#   6 - Recursos Compartidos + Concurrencia
# ESPACIO - Iniciar simulacion
# R       - Reiniciar
# ============================================================

# -------------------------------------------------------
# ESTADO GLOBAL
# -------------------------------------------------------
current_mode = 0   # 0 = pantalla de inicio
data_lock    = threading.Lock()

# -------------------------------------------------------
# COLORES
# -------------------------------------------------------
THREAD_COLORS = [
    (255, 80,  80),
    (80,  180, 255),
    (80,  255, 140),
    (255, 180, 50),
    (200, 80,  255),
]

MODE_NAMES = {
    1: "1. CONDICION DE CARRERA",
    2: "2. SEMAFORO",
    3: "3. MUTEX + SECCION CRITICA",
    4: "4. DEADLOCK",
    5: "5. MONITOR",
    6: "6. RECURSOS COMPARTIDOS + CONCURRENCIA",
}

# ================================================================
# MODO 1: CONDICION DE CARRERA
# ================================================================
rc_shared_counter = 0
rc_thread_data    = []
rc_running        = False
rc_finished       = False
rc_result_text    = ""
RC_ITERATIONS     = 30

def rc_unsafe_increment(thread_id):
    global rc_shared_counter, rc_finished, rc_result_text
    for i in range(RC_ITERATIONS):
        temp = rc_shared_counter
        time.sleep(random.uniform(0.03, 0.07))
        temp += 1
        rc_shared_counter = temp
        with data_lock:
            rc_thread_data[thread_id]["progress"]     = i + 1
            rc_thread_data[thread_id]["counter_seen"] = temp
            rc_thread_data[thread_id]["active"]       = True
        time.sleep(random.uniform(0.02, 0.05))
    with data_lock:
        rc_thread_data[thread_id]["done"]   = True
        rc_thread_data[thread_id]["active"] = False
    all_done = all(t["done"] for t in rc_thread_data)
    if all_done:
        expected       = RC_ITERATIONS * 2
        lost           = expected - rc_shared_counter
        rc_result_text = "Esperados: {}   Registrados: {}   Perdidos: {}".format(
            expected, rc_shared_counter, lost)
        rc_finished = True

def rc_start():
    global rc_shared_counter, rc_running, rc_finished, rc_result_text, rc_thread_data
    rc_shared_counter = 0
    rc_running        = True
    rc_finished       = False
    rc_result_text    = ""
    rc_thread_data    = [
        {"id": 0, "progress": 0, "counter_seen": 0, "done": False, "active": False},
        {"id": 1, "progress": 0, "counter_seen": 0, "done": False, "active": False},
    ]
    t1 = threading.Thread(target=rc_unsafe_increment, args=(0,)); t1.daemon = True; t1.start()
    time.sleep(0.05)
    t2 = threading.Thread(target=rc_unsafe_increment, args=(1,)); t2.daemon = True; t2.start()

def rc_reset():
    global rc_shared_counter, rc_running, rc_finished, rc_result_text, rc_thread_data
    rc_shared_counter = 0
    rc_running        = False
    rc_finished       = False
    rc_result_text    = ""
    with data_lock:
        rc_thread_data = []

# ================================================================
# MODO 2: SEMAFORO
# ================================================================
SEM_MAX_SLOTS  = 2
SEM_NUM        = 5
sem_semaphore  = threading.Semaphore(SEM_MAX_SLOTS)
sem_thread_data = []
sem_running    = False
sem_finished   = False

def sem_worker(thread_id):
    global sem_finished
    with data_lock:
        sem_thread_data[thread_id]["state"] = "EN FILA"
    sem_semaphore.acquire()
    with data_lock:
        sem_thread_data[thread_id]["state"]  = "COMIENDO"
        sem_thread_data[thread_id]["inside"] = True
    eat_time = random.uniform(1.5, 3.5)
    steps = 20
    for s in range(steps):
        time.sleep(eat_time / steps)
        with data_lock:
            sem_thread_data[thread_id]["progress"] = int(100 * (s + 1) / steps)
    sem_semaphore.release()
    with data_lock:
        sem_thread_data[thread_id]["state"]  = "SE FUE"
        sem_thread_data[thread_id]["inside"] = False
        sem_thread_data[thread_id]["done"]   = True
    if all(t["done"] for t in sem_thread_data):
        sem_finished = True

def sem_start():
    global sem_semaphore, sem_thread_data, sem_running, sem_finished
    sem_semaphore   = threading.Semaphore(SEM_MAX_SLOTS)
    sem_running     = True
    sem_finished    = False
    sem_thread_data = [{"id": i, "state": "EN ESPERA", "inside": False,
                        "done": False, "progress": 0} for i in range(SEM_NUM)]
    for i in range(SEM_NUM):
        t = threading.Thread(target=sem_worker, args=(i,)); t.daemon = True; t.start()
        time.sleep(0.08)

def sem_reset():
    global sem_semaphore, sem_thread_data, sem_running, sem_finished
    sem_semaphore = threading.Semaphore(SEM_MAX_SLOTS)
    sem_running   = False
    sem_finished  = False
    with data_lock:
        sem_thread_data = []

# ================================================================
# MODO 3: MUTEX + SECCION CRITICA
# ================================================================
mutex_lock       = threading.Lock()
mutex_thread_data = []
mutex_running    = False
mutex_finished   = False
MUTEX_NUM        = 4
MUTEX_DISHES     = ["preparando sopa...", "cortando verduras...",
                    "cocinando carne...", "emplatando..."]

def mutex_worker(thread_id):
    global mutex_finished
    with data_lock:
        if thread_id >= len(mutex_thread_data): return
        mutex_thread_data[thread_id]["state"] = "ESPERANDO COCINA"

    mutex_lock.acquire()

    with data_lock:
        if thread_id >= len(mutex_thread_data):
            mutex_lock.release()
            return
        mutex_thread_data[thread_id]["state"]  = "EN LA COCINA"
        mutex_thread_data[thread_id]["inside"] = True

    cook_time = random.uniform(1.5, 3.0)
    steps = 20
    for s in range(steps):
        time.sleep(cook_time / steps)
        with data_lock:
            if thread_id >= len(mutex_thread_data):
                mutex_lock.release()
                return
            mutex_thread_data[thread_id]["progress"] = int(100 * (s + 1) / steps)
            if s % 5 == 0:
                mutex_thread_data[thread_id]["dish"] = random.choice(MUTEX_DISHES)

    mutex_lock.release()

    with data_lock:
        if thread_id >= len(mutex_thread_data): return
        mutex_thread_data[thread_id]["state"]  = "PLATO LISTO"
        mutex_thread_data[thread_id]["inside"] = False
        mutex_thread_data[thread_id]["done"]   = True

    if all(t["done"] for t in mutex_thread_data):
        mutex_finished = True

def mutex_start():
    global mutex_lock, mutex_thread_data, mutex_running, mutex_finished
    mutex_lock        = threading.Lock()
    mutex_running     = True
    mutex_finished    = False
    mutex_thread_data = [{"id": i, "state": "EN ESPERA", "inside": False,
                          "done": False, "progress": 0, "dish": MUTEX_DISHES[0]}
                         for i in range(MUTEX_NUM)]
    for i in range(MUTEX_NUM):
        t = threading.Thread(target=mutex_worker, args=(i,)); t.daemon = True; t.start()
        time.sleep(0.1)

def mutex_reset():
    global mutex_lock, mutex_thread_data, mutex_running, mutex_finished
    mutex_lock        = threading.Lock()
    mutex_running     = False
    mutex_finished    = False
    with data_lock:
        mutex_thread_data = []

# ================================================================
# MODO 4: DEADLOCK
# ================================================================
dl_tenedor   = threading.Lock()
dl_cuchillo  = threading.Lock()
dl_thread_data = []
dl_running   = False
dl_finished  = False

def dl_mesero1():
    global dl_finished
    with data_lock:
        dl_thread_data[0].update({"state": "ESPERANDO TENEDOR", "wants": "tenedor", "has": ""})
    dl_tenedor.acquire()
    with data_lock:
        dl_thread_data[0].update({"state": "TIENE TENEDOR, ESPERA CUCHILLO",
                                   "has": "tenedor", "wants": "cuchillo", "blocked": True})
    time.sleep(0.5)
    dl_cuchillo.acquire()
    with data_lock:
        dl_thread_data[0].update({"state": "SIRVIENDO PLATO", "blocked": False, "done": True})
    dl_cuchillo.release(); dl_tenedor.release()

def dl_mesero2():
    global dl_finished
    with data_lock:
        dl_thread_data[1].update({"state": "ESPERANDO CUCHILLO", "wants": "cuchillo", "has": ""})
    dl_cuchillo.acquire()
    with data_lock:
        dl_thread_data[1].update({"state": "TIENE CUCHILLO, ESPERA TENEDOR",
                                   "has": "cuchillo", "wants": "tenedor", "blocked": True})
    time.sleep(0.5)
    dl_tenedor.acquire()
    with data_lock:
        dl_thread_data[1].update({"state": "SIRVIENDO PLATO", "blocked": False, "done": True})
    dl_tenedor.release(); dl_cuchillo.release()

def dl_start():
    global dl_tenedor, dl_cuchillo, dl_thread_data, dl_running, dl_finished
    dl_tenedor    = threading.Lock()
    dl_cuchillo   = threading.Lock()
    dl_running    = True
    dl_finished   = False
    dl_thread_data = [
        {"id": 0, "state": "EN ESPERA", "has": "", "wants": "", "blocked": False, "done": False},
        {"id": 1, "state": "EN ESPERA", "has": "", "wants": "", "blocked": False, "done": False},
    ]
    t1 = threading.Thread(target=dl_mesero1); t1.daemon = True; t1.start()
    time.sleep(0.1)
    t2 = threading.Thread(target=dl_mesero2); t2.daemon = True; t2.start()

def dl_reset():
    global dl_tenedor, dl_cuchillo, dl_thread_data, dl_running, dl_finished
    dl_tenedor  = threading.Lock()
    dl_cuchillo = threading.Lock()
    dl_running  = False
    dl_finished = False
    with data_lock:
        dl_thread_data = []

# ================================================================
# MODO 5: MONITOR
# ================================================================
# El monitor es como el jefe de cocina que coordina todo.
# Los meseros le piden permiso al jefe antes de usar la cocina.
# El jefe lleva un registro interno y avisa cuando hay espacio.
# ================================================================
class MonitorCocina(object):
    def __init__(self):
        self._lock      = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self.capacidad  = 2
        self.ocupado    = 0
        self.historial  = []

    def entrar(self, mesero_id):
        with self._condition:
            while self.ocupado >= self.capacidad:
                self._condition.wait()
            self.ocupado += 1
            self.historial.append("M{} entro (ocupado={})".format(mesero_id + 1, self.ocupado))

    def salir(self, mesero_id):
        with self._condition:
            self.ocupado -= 1
            self.historial.append("M{} salio  (ocupado={})".format(mesero_id + 1, self.ocupado))
            self._condition.notify_all()

    def get_estado(self):
        with self._lock:
            return self.ocupado, list(self.historial[-6:])

monitor_obj     = MonitorCocina()
mon_thread_data = []
mon_running     = False
mon_finished    = False
MON_NUM         = 5

def mon_worker(thread_id):
    global mon_finished
    with data_lock:
        mon_thread_data[thread_id]["state"] = "PIDIENDO PERMISO"
    monitor_obj.entrar(thread_id)
    with data_lock:
        mon_thread_data[thread_id]["state"]  = "COCINANDO"
        mon_thread_data[thread_id]["inside"] = True
    work_time = random.uniform(1.5, 3.0)
    steps = 20
    for s in range(steps):
        time.sleep(work_time / steps)
        with data_lock:
            mon_thread_data[thread_id]["progress"] = int(100 * (s + 1) / steps)
    monitor_obj.salir(thread_id)
    with data_lock:
        mon_thread_data[thread_id]["state"]  = "LISTO"
        mon_thread_data[thread_id]["inside"] = False
        mon_thread_data[thread_id]["done"]   = True
    if all(t["done"] for t in mon_thread_data):
        mon_finished = True

def mon_start():
    global monitor_obj, mon_thread_data, mon_running, mon_finished
    monitor_obj     = MonitorCocina()
    mon_running     = True
    mon_finished    = False
    mon_thread_data = [{"id": i, "state": "EN ESPERA", "inside": False,
                        "done": False, "progress": 0} for i in range(MON_NUM)]
    for i in range(MON_NUM):
        t = threading.Thread(target=mon_worker, args=(i,)); t.daemon = True; t.start()
        time.sleep(0.08)

def mon_reset():
    global monitor_obj, mon_thread_data, mon_running, mon_finished
    monitor_obj     = MonitorCocina()
    mon_running     = False
    mon_finished    = False
    with data_lock:
        mon_thread_data = []

# ================================================================
# MODO 6: RECURSOS COMPARTIDOS + CONCURRENCIA + SINCRONIZACION
# ================================================================
# Tres recursos del restaurante: caja registradora, bodega, impresora
# Varios meseros los usan al mismo tiempo de forma coordinada.
# Muestra concurrencia real: varios hilos activos simultaneamente.
# ================================================================
REC_NAMES  = ["Caja", "Bodega", "Impresora"]
REC_COLORS = [(255, 200, 50), (80, 220, 120), (180, 120, 255)]
rec_locks       = [threading.Lock(), threading.Lock(), threading.Lock()]
rec_thread_data = []
rec_resource_data = []
rec_running     = False
rec_finished    = False
REC_NUM         = 6

def rec_worker(thread_id):
    global rec_finished
    recursos_a_usar = random.sample([0, 1, 2], random.randint(1, 2))
    with data_lock:
        rec_thread_data[thread_id]["recursos"] = recursos_a_usar
        rec_thread_data[thread_id]["state"]    = "LISTO PARA TRABAJAR"
    time.sleep(random.uniform(0.1, 0.5))

    for rid in recursos_a_usar:
        with data_lock:
            rec_thread_data[thread_id]["state"]       = "ESPERANDO {}".format(REC_NAMES[rid])
            rec_thread_data[thread_id]["waiting_for"] = rid

        rec_locks[rid].acquire()

        with data_lock:
            rec_thread_data[thread_id]["state"]       = "USANDO {}".format(REC_NAMES[rid])
            rec_thread_data[thread_id]["waiting_for"] = -1
            rec_thread_data[thread_id]["using"]       = rid
            rec_resource_data[rid]["user"]            = thread_id
            rec_resource_data[rid]["busy"]            = True

        use_time = random.uniform(0.8, 2.0)
        steps = 15
        for s in range(steps):
            time.sleep(use_time / steps)
            with data_lock:
                rec_thread_data[thread_id]["progress"] = int(100 * (s + 1) / steps)

        rec_locks[rid].release()

        with data_lock:
            rec_resource_data[rid]["user"] = -1
            rec_resource_data[rid]["busy"] = False
            rec_thread_data[thread_id]["using"]    = -1
            rec_thread_data[thread_id]["progress"] = 0

    with data_lock:
        rec_thread_data[thread_id]["state"] = "TERMINO TURNO"
        rec_thread_data[thread_id]["done"]  = True

    if all(t["done"] for t in rec_thread_data):
        rec_finished = True

def rec_start():
    global rec_locks, rec_thread_data, rec_resource_data, rec_running, rec_finished
    rec_locks         = [threading.Lock(), threading.Lock(), threading.Lock()]
    rec_running       = True
    rec_finished      = False
    rec_resource_data = [{"id": i, "busy": False, "user": -1} for i in range(3)]
    rec_thread_data   = [{"id": i, "state": "EN ESPERA", "done": False, "progress": 0,
                          "recursos": [], "using": -1, "waiting_for": -1}
                         for i in range(REC_NUM)]
    for i in range(REC_NUM):
        t = threading.Thread(target=rec_worker, args=(i,)); t.daemon = True; t.start()
        time.sleep(0.1)

def rec_reset():
    global rec_locks, rec_thread_data, rec_resource_data, rec_running, rec_finished
    rec_locks         = [threading.Lock(), threading.Lock(), threading.Lock()]
    rec_running       = False
    rec_finished      = False
    with data_lock:
        rec_thread_data   = []
        rec_resource_data = []

# ================================================================
# VARIABLES DE ANIMACION GLOBAL
# ================================================================
pulse_timer = 0

# ================================================================
# PROCESSING: setup / draw / keyPressed
# ================================================================
def setup():
    size(1000, 1000)
    frameRate(30)

def draw():
    global pulse_timer
    pulse_timer += 1
    background(30, 18, 10)

    if current_mode == 0:
        draw_menu()
    elif current_mode == 1:
        draw_rc()
    elif current_mode == 2:
        draw_sem()
    elif current_mode == 3:
        draw_mutex()
    elif current_mode == 4:
        draw_dl()
    elif current_mode == 5:
        draw_monitor()
    elif current_mode == 6:
        draw_rec()

    draw_topbar()

# ================================================================
# BARRA SUPERIOR (siempre visible)
# ================================================================
def draw_topbar():
    if current_mode == 0:
        return
    fill(20, 12, 5, 200)
    noStroke()
    rect(0, 0, width, 22)
    fill(160, 130, 80)
    textSize(10)
    textAlign(LEFT)
    noStroke()
    text("  [1] Carrera  [2] Semaforo  [3] Mutex  [4] Deadlock  [5] Monitor  [6] Recursos  |  [ESPACIO] Iniciar  [R] Reiniciar", 0, 14)

# ================================================================
# PANTALLA DE INICIO
# ================================================================
def draw_menu():
    # Titulo
    fill(255, 220, 50)
    textSize(22)
    textAlign(CENTER)
    noStroke()
    text("SIMULADOR DE CONCURRENCIA", width / 2, 70)

    fill(200, 170, 130)
    textSize(13)
    textAlign(CENTER)
    text("Analogia: Restaurante", width / 2, 95)

    # Separador
    stroke(120, 90, 40)
    strokeWeight(1)
    line(100, 110, width - 100, 110)

    # Modos disponibles
    descriptions = {
        1: "Dos meseros anotan pedidos sin coordinacion. Se pierden registros.",
        2: "El restaurante tiene N mesas. Clientes esperan en fila si esta lleno.",
        3: "Solo UN mesero puede entrar a la cocina. Los demas esperan afuera.",
        4: "Dos meseros se bloquean mutuamente esperando el utensilio del otro.",
        5: "El jefe de cocina coordina el acceso con condiciones de espera.",
        6: "Varios meseros usan caja, bodega e impresora de forma concurrente.",
    }

    for i in range(1, 7):
        by = 140 + (i - 1) * 68
        c  = THREAD_COLORS[(i - 1) % len(THREAD_COLORS)]

        fill(40, 25, 10)
        noStroke()
        rect(80, by, width - 160, 55, 8)

        stroke(c[0], c[1], c[2])
        strokeWeight(1.5)
        noFill()
        rect(80, by, width - 160, 55, 8)

        fill(c[0], c[1], c[2])
        noStroke()
        textSize(13)
        textAlign(LEFT)
        text("[{}]  {}".format(i, MODE_NAMES[i]), 100, by + 20)

        fill(180, 155, 115)
        textSize(10)
        textAlign(LEFT)
        text(descriptions[i], 100, by + 38)

    fill(140, 120, 80)
    textSize(11)
    textAlign(CENTER)
    noStroke()
    text("Presiona una tecla del 1 al 6 para elegir un modo", width / 2, 565)

# ================================================================
# DRAW MODO 1: CONDICION DE CARRERA
# ================================================================
def draw_rc():
    fill(255, 220, 50)
    textSize(16)
    textAlign(CENTER)
    noStroke()
    text("CONDICION DE CARRERA - Restaurante", width / 2, 42)

    fill(200, 170, 130)
    textSize(10)
    textAlign(CENTER)
    text("Dos meseros anotan pedidos en el mismo cuaderno SIN coordinacion", width / 2, 58)

    # Cuaderno
    fill(0, 0, 0, 80)
    noStroke()
    rect(308, 73, 130, 90, 6)
    fill(245, 235, 200)
    stroke(180, 140, 80)
    strokeWeight(2)
    rect(303, 68, 130, 90, 6)
    stroke(150, 120, 60)
    strokeWeight(1.5)
    for i in range(6):
        ellipse(303, 82 + i * 14, 10, 10)
    fill(80, 50, 20)
    noStroke()
    textSize(10)
    textAlign(CENTER)
    text("CUADERNO DE PEDIDOS", 368, 86)
    stroke(180, 160, 120, 120)
    strokeWeight(1)
    for i in range(3):
        line(318, 100 + i * 14, 423, 100 + i * 14)
    fill(180, 60, 40)
    noStroke()
    textSize(11)
    textAlign(CENTER)
    text("Total pedidos:", 368, 116)
    fill(180, 60, 40)
    textSize(28)
    textAlign(CENTER)
    text(str(rc_shared_counter), 368, 148)

    # Mesa
    fill(120, 80, 40)
    noStroke()
    rect(270, 175, 200, 12, 4)
    fill(80, 50, 25)
    rect(340, 187, 12, 30, 2)
    rect(380, 187, 12, 30, 2)

    with data_lock:
        snap = list(rc_thread_data)

    y_positions = [290, 400]
    for td in snap:
        tid    = td["id"]
        prog   = td["progress"]
        c      = THREAD_COLORS[tid]
        y_base = y_positions[tid]
        done   = td["done"]
        active = td["active"]

        fill(50, 30, 15)
        noStroke()
        rect(50, y_base - 12, 200, 16, 4)
        fill(c[0], c[1], c[2])
        bar_w = int(200 * prog / float(RC_ITERATIONS))
        if bar_w > 0:
            rect(50, y_base - 12, bar_w, 16, 4)

        fill(230, 200, 150)
        textSize(12)
        textAlign(LEFT)
        noStroke()
        text("Mesero {}".format(tid + 1), 50, y_base - 18)

        progress_ratio = prog / float(RC_ITERATIONS)
        cx = int(55 + progress_ratio * 200)
        cy = y_base - 4

        if done:
            fill(c[0], c[1], c[2], 100); stroke(200, 200, 200, 80)
        else:
            fill(c[0], c[1], c[2]); stroke(255, 255, 255)
        strokeWeight(1.5)
        ellipse(cx, cy, 32, 32)
        fill(255) if not done else fill(180, 180, 180)
        noStroke()
        textSize(11)
        textAlign(CENTER)
        text("M{}".format(tid + 1), cx, cy + 4)

        textSize(10)
        textAlign(LEFT)
        noStroke()
        if done:
            fill(100, 220, 100)
            text("TURNO TERMINADO", 390, y_base - 8)
        elif active:
            fill(255, 200, 50)
            text("ANOTANDO PEDIDO", 390, y_base - 8)
        else:
            fill(160, 140, 110)
            text("EN ESPERA", 390, y_base - 8)

        if active or done:
            fill(180, 160, 120)
            textSize(10)
            textAlign(LEFT)
            text("Anoto pedido #{}".format(td["counter_seen"]), 390, y_base + 10)

        fill(140, 120, 90)
        textSize(10)
        textAlign(LEFT)
        text("{}/{}".format(prog, RC_ITERATIONS), 260, y_base + 8)

        stroke(c[0], c[1], c[2], 150)
        strokeWeight(1.2)
        line(cx + 16, cy - 8, 368 - 10, 155)

    if rc_finished and rc_result_text != "":
        fill(200, 60, 50, 230)
        noStroke()
        rect(40, 465, 680, 55, 8)
        fill(255)
        textSize(12)
        textAlign(CENTER)
        text(rc_result_text, width / 2, 487)
        fill(255, 220, 80)
        textSize(10)
        textAlign(CENTER)
        text("Pedidos perdidos = condicion de carrera: los meseros pisaron el registro del otro", width / 2, 506)

    draw_bottom_hint(rc_running,
        "El cuaderno deberia tener {} pedidos. Si hay menos, hubo condicion de carrera.".format(RC_ITERATIONS * 2))

# ================================================================
# DRAW MODO 2: SEMAFORO
# ================================================================
SEM_ZX = 255
SEM_ZY = 100
SEM_ZW = 240
SEM_ZH = 260

def draw_sem():
    fill(255, 220, 50)
    textSize(16)
    textAlign(CENTER)
    noStroke()
    text("SEMAFORO - Restaurante", width / 2, 42)
    fill(200, 170, 130)
    textSize(10)
    textAlign(CENTER)
    text("Maximo {} clientes pueden comer al mismo tiempo. Los demas esperan en fila.".format(SEM_MAX_SLOTS), width / 2, 58)

    with data_lock:
        snap = list(sem_thread_data)

    inside_count = sum(1 for t in snap if t["inside"])
    slots_free   = SEM_MAX_SLOTS - inside_count

    # Restaurante
    fill(0, 0, 0, 80); noStroke(); rect(SEM_ZX + 4, SEM_ZY + 4, SEM_ZW, SEM_ZH, 10)
    fill(60, 35, 15); stroke(180, 130, 60); strokeWeight(2)
    rect(SEM_ZX, SEM_ZY, SEM_ZW, SEM_ZH, 10)
    fill(180, 130, 60); noStroke()
    rect(SEM_ZX + 30, SEM_ZY - 18, SEM_ZW - 60, 26, 4)
    fill(30, 15, 5); textSize(12); textAlign(CENTER)
    text("RESTAURANTE", SEM_ZX + SEM_ZW / 2, SEM_ZY - 1)

    # Mesas
    slot_w = 88; slot_h = 88; slot_pad = 14
    total_w = SEM_MAX_SLOTS * slot_w + (SEM_MAX_SLOTS - 1) * slot_pad
    sx0 = int(SEM_ZX + (SEM_ZW - total_w) / 2)
    for s in range(SEM_MAX_SLOTS):
        sx = sx0 + s * (slot_w + slot_pad)
        sy = SEM_ZY + 28
        occupant = None
        cnt = 0
        for t in snap:
            if t["inside"]:
                if cnt == s: occupant = t
                cnt += 1
        if occupant is not None:
            c = THREAD_COLORS[occupant["id"]]
            fill(c[0], c[1], c[2], 60); stroke(c[0], c[1], c[2]); strokeWeight(2)
            rect(sx, sy, slot_w, slot_h, 8)
            fill(120, 80, 40); noStroke()
            ellipse(sx + slot_w / 2, sy + 36, 46, 22)
            rect(sx + slot_w / 2 - 4, sy + 46, 8, 18, 2)
            fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(1.5)
            ellipse(sx + slot_w / 2, sy + 20, 30, 30)
            fill(255); noStroke(); textSize(9); textAlign(CENTER)
            text("C{}".format(occupant["id"] + 1), sx + slot_w / 2, sy + 24)
            fill(40, 25, 10); noStroke()
            rect(sx + 6, sy + 66, slot_w - 12, 10, 3)
            pw = int((slot_w - 12) * occupant["progress"] / 100.0)
            if pw > 0:
                fill(c[0], c[1], c[2]); rect(sx + 6, sy + 66, pw, 10, 3)
            fill(230, 200, 150); textSize(8); textAlign(CENTER)
            text("{}%".format(occupant["progress"]), sx + slot_w / 2, sy + 86)
        else:
            fill(45, 28, 12); stroke(140, 100, 50, 120); strokeWeight(1)
            rect(sx, sy, slot_w, slot_h, 8)
            fill(120, 80, 40); noStroke()
            ellipse(sx + slot_w / 2, sy + 36, 46, 22)
            rect(sx + slot_w / 2 - 4, sy + 46, 8, 18, 2)
            fill(140, 100, 60, 150); textSize(10); textAlign(CENTER)
            text("MESA LIBRE", sx + slot_w / 2, sy + 76)

    # Contador semaforo
    fill(30, 20, 8); noStroke()
    rect(SEM_ZX + 20, SEM_ZY + 130, SEM_ZW - 40, 50, 8)
    fill(200, 170, 100); textSize(10); textAlign(CENTER)
    text("Mesas disponibles", SEM_ZX + SEM_ZW / 2, SEM_ZY + 150)
    sem_col = color(80, 220, 100) if slots_free > 0 else color(255, 70, 70)
    fill(sem_col); textSize(24); textAlign(CENTER)
    text("{} / {}".format(slots_free, SEM_MAX_SLOTS), SEM_ZX + SEM_ZW / 2, SEM_ZY + 174)

    # Luz semaforo
    lx = int(SEM_ZX + SEM_ZW / 2); ly = SEM_ZY + 218
    stroke(150, 120, 60); strokeWeight(3)
    line(lx, ly - 16, lx, ly + 20)
    if slots_free > 0:
        fill(60, 220, 80); stroke(60, 220, 80)
    else:
        fill(220, 60, 60); stroke(220, 60, 60)
    strokeWeight(2); ellipse(lx, ly, 30, 30)
    fill(255); noStroke(); textSize(8); textAlign(CENTER)
    text("PASA" if slots_free > 0 else "LLENO", lx, ly + 20)

    # Puerta
    fill(100, 65, 25); noStroke()
    rect(SEM_ZX + SEM_ZW / 2 - 16, SEM_ZY + SEM_ZH - 34, 32, 34, 4)
    fill(180, 140, 60)
    ellipse(SEM_ZX + SEM_ZW / 2 + 8, SEM_ZY + SEM_ZH - 18, 6, 6)

    # Fila izquierda
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(CENTER)
    text("FILA", 105, SEM_ZY + 18)
    stroke(150, 120, 60); strokeWeight(1)
    line(55, SEM_ZY + 28, 55, SEM_ZY + 235)
    line(55, SEM_ZY + 28, 175, SEM_ZY + 28)
    line(175, SEM_ZY + 28, 175, SEM_ZY + 235)
    waiting = [t for t in snap if t["state"] == "EN FILA"]
    for idx, t in enumerate(waiting):
        c = THREAD_COLORS[t["id"]]
        wx = 115; wy = SEM_ZY + 52 + idx * 46
        fill(0, 0, 0, 50); noStroke(); ellipse(wx + 2, wy + 2, 34, 34)
        fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(1.5)
        ellipse(wx, wy, 34, 34)
        fill(255); noStroke(); textSize(9); textAlign(CENTER)
        text("C{}".format(t["id"] + 1), wx, wy + 4)
        stroke(c[0], c[1], c[2], 150); strokeWeight(1.2)
        line(wx + 17, wy, SEM_ZX - 3, SEM_ZY + SEM_ZH / 2)

    # Lista derecha
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(LEFT)
    text("CLIENTES", 535, SEM_ZY + 18)
    for t in snap:
        tid = t["id"]; c = THREAD_COLORS[tid]
        ty = SEM_ZY + 35 + tid * 46
        fill(c[0], c[1], c[2], 100 if t["done"] else 255); noStroke()
        ellipse(548, ty, 26, 26)
        fill(255) if not t["done"] else fill(160, 160, 160)
        textSize(9); textAlign(CENTER)
        text("C{}".format(tid + 1), 548, ty + 4)
        state = t["state"]
        if state == "SE FUE": fill(100, 220, 100)
        elif state == "COMIENDO": fill(255, 200, 50)
        elif state == "EN FILA": fill(200, 140, 60)
        else: fill(160, 140, 110)
        textSize(9); textAlign(LEFT); noStroke()
        text(state, 563, ty + 4)

    if sem_finished:
        fill(30, 60, 30, 220); noStroke(); rect(40, 400, 680, 45, 10)
        fill(80, 220, 120); textSize(12); textAlign(CENTER)
        text("Todos los clientes atendidos. El semaforo controlo el acceso correctamente.", width / 2, 427)

    draw_bottom_hint(sem_running,
        "Semaforo = capacidad del restaurante. Nunca mas de {} clientes al mismo tiempo.".format(SEM_MAX_SLOTS))

# ================================================================
# DRAW MODO 3: MUTEX + SECCION CRITICA
# ================================================================
KX = 265; KY = 90; KW = 230; KH = 230

def draw_mutex():
    fill(255, 220, 50); textSize(16); textAlign(CENTER); noStroke()
    text("MUTEX + SECCION CRITICA - Restaurante", width / 2, 42)
    fill(200, 170, 130); textSize(10); textAlign(CENTER)
    text("Solo UN mesero puede estar en la cocina a la vez. Los demas esperan afuera.", width / 2, 58)

    with data_lock:
        snap = list(mutex_thread_data)

    if len(snap) == 0:
        fill(160, 140, 110); textSize(13); textAlign(CENTER)
        text("Presiona [ESPACIO] para iniciar", width / 2, 300)
        draw_bottom_hint(False, "Mutex = candado. Seccion critica = cocina. Solo 1 mesero adentro.")
        return

    current = next((t for t in snap if t["inside"]), None)
    mutex_free = current is None

    # Cocina
    fill(0, 0, 0, 80); noStroke(); rect(KX + 5, KY + 5, KW, KH, 10)
    if not mutex_free:
        c = THREAD_COLORS[current["id"]]; stroke(c[0], c[1], c[2])
    else:
        stroke(140, 100, 50)
    strokeWeight(2); fill(45, 28, 12); rect(KX, KY, KW, KH, 10)
    fill(140, 100, 50); noStroke()
    rect(KX + 25, KY - 20, KW - 50, 28, 4)
    fill(30, 15, 5); textSize(11); textAlign(CENTER)
    text("COCINA (Seccion Critica)", KX + KW / 2, KY - 2)

    # Decoracion cocina
    fill(60, 40, 20); noStroke(); rect(KX + 14, KY + 155, 55, 40, 4)
    stroke(180, 100, 40); strokeWeight(1.5); noFill()
    ellipse(KX + 29, KY + 167, 18, 18); ellipse(KX + 51, KY + 167, 18, 18)
    ellipse(KX + 29, KY + 184, 18, 18); ellipse(KX + 51, KY + 184, 18, 18)
    fill(80, 55, 25); noStroke(); rect(KX + 78, KY + 158, 122, 14, 3)
    fill(100, 80, 40); noStroke()
    ellipse(KX + 104, KY + 155, 22, 16)
    ellipse(KX + 139, KY + 155, 22, 16)
    ellipse(KX + 174, KY + 155, 22, 16)

    # Mesero dentro
    if current is not None:
        c = THREAD_COLORS[current["id"]]
        kx2 = int(KX + KW / 2); ky2 = KY + 75
        fill(c[0], c[1], c[2], 40); noStroke(); ellipse(kx2, ky2, 80, 80)
        fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(2)
        ellipse(kx2, ky2, 48, 48)
        fill(255); noStroke(); textSize(13); textAlign(CENTER)
        text("M{}".format(current["id"] + 1), kx2, ky2 + 5)
        fill(230, 200, 150); textSize(10); textAlign(CENTER); noStroke()
        text("Mesero {}".format(current["id"] + 1), kx2, ky2 + 33)
        fill(40, 25, 10); noStroke()
        rect(KX + 20, KY + 112, KW - 40, 13, 4)
        pw = int((KW - 40) * current["progress"] / 100.0)
        if pw > 0:
            fill(c[0], c[1], c[2]); rect(KX + 20, KY + 112, pw, 13, 4)
        fill(255); textSize(9); textAlign(CENTER)
        text("{}%".format(current["progress"]), KX + KW / 2, KY + 124)
        fill(200, 170, 110); textSize(9); textAlign(CENTER)
        text(current["dish"], KX + KW / 2, KY + 142)
    else:
        fill(100, 75, 40); textSize(12); textAlign(CENTER); noStroke()
        text("COCINA LIBRE", KX + KW / 2, KY + 85)

    # Candado mutex
    lx2 = int(KX + KW / 2); ly2 = KY + KH - 28
    if mutex_free:
        lc = color(80, 200, 100)
    else:
        c2 = THREAD_COLORS[current["id"]]; lc = color(c2[0], c2[1], c2[2])
    fill(lc); noStroke(); rect(lx2 - 13, ly2, 26, 20, 4)
    noFill(); stroke(lc); strokeWeight(3)
    if mutex_free:
        arc(lx2, ly2 - 2, 20, 20, PI, TWO_PI)
    else:
        arc(lx2, ly2 + 1, 20, 20, PI, TWO_PI)
    fill(255); noStroke(); textSize(8); textAlign(CENTER)
    text("MUTEX", lx2, ly2 + 13)
    fill(lc); textSize(9); textAlign(CENTER)
    text("LIBRE" if mutex_free else "OCUPADO", lx2, ly2 + 30)

    # Fila
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(CENTER)
    text("FILA DE ESPERA", 108, KY + 18)
    stroke(150, 120, 60); strokeWeight(1); noFill()
    rect(58, KY + 28, 100, 195, 4)
    waiting = [t for t in snap if t["state"] == "ESPERANDO COCINA"]
    for idx, t in enumerate(waiting):
        c = THREAD_COLORS[t["id"]]
        wx = 108; wy = KY + 54 + idx * 50
        fill(0, 0, 0, 50); noStroke(); ellipse(wx + 2, wy + 2, 34, 34)
        fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(1.5)
        ellipse(wx, wy, 34, 34)
        fill(255); noStroke(); textSize(11); textAlign(CENTER)
        text("M{}".format(t["id"] + 1), wx, wy + 4)
        stroke(c[0], c[1], c[2], 130); strokeWeight(1.2)
        line(wx + 17, wy, KX - 2, KY + KH / 2)

    # Lista derecha
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(LEFT)
    text("MESEROS", 548, KY + 18)
    for t in snap:
        tid = t["id"]; c = THREAD_COLORS[tid]
        ty = KY + 36 + tid * 50
        fill(c[0], c[1], c[2], 100 if t["done"] else 255); noStroke()
        ellipse(558, ty, 26, 26)
        fill(255) if not t["done"] else fill(160, 160, 160)
        textSize(10); textAlign(CENTER)
        text("M{}".format(tid + 1), 558, ty + 4)
        state = t["state"]
        if state == "PLATO LISTO": fill(100, 220, 100)
        elif state == "EN LA COCINA": fill(255, 200, 50)
        elif state == "ESPERANDO COCINA": fill(200, 120, 60)
        else: fill(160, 140, 110)
        textSize(9); textAlign(LEFT); noStroke()
        text(state, 573, ty + 4)

    if mutex_finished:
        fill(30, 60, 30, 220); noStroke(); rect(40, 390, 680, 45, 10)
        fill(80, 220, 120); textSize(12); textAlign(CENTER)
        text("Todos los meseros cocinaron. El mutex garantizo exclusion mutua.", width / 2, 417)

    draw_bottom_hint(mutex_running,
        "Mutex = candado de la cocina. Seccion critica = cocina. Solo 1 mesero adentro.")

# ================================================================
# DRAW MODO 4: DEADLOCK
# ================================================================
DL_TX = 230; DL_TY = 210
DL_CX = 530; DL_CY = 210
DL_M1X = 120; DL_M1Y = 340
DL_M2X = 640; DL_M2Y = 340

def draw_dl():
    fill(255, 220, 50); textSize(16); textAlign(CENTER); noStroke()
    text("DEADLOCK - Restaurante", width / 2, 42)
    fill(200, 170, 130); textSize(10); textAlign(CENTER)
    text("Cada mesero tiene un utensilio y espera el del otro. Ninguno suelta el suyo.", width / 2, 58)

    with data_lock:
        snap = list(dl_thread_data)

    if len(snap) < 2:
        fill(160, 140, 110); textSize(13); textAlign(CENTER)
        text("Presiona [ESPACIO] para iniciar", width / 2, 300)
        draw_bottom_hint(False, "Deadlock = bloqueo circular. Solucion: mismo orden de adquisicion.")
        return

    td1 = snap[0]; td2 = snap[1]
    both_blocked = td1["blocked"] and td2["blocked"]

    if both_blocked:
        pulse = abs(sin(pulse_timer * 0.08))
        fill(180, 30, 30, int(40 * pulse)); noStroke()
        rect(0, 0, width, height)

    # Recursos
    dl_draw_resource(DL_TX, DL_TY, "TENEDOR",  td1, both_blocked)
    dl_draw_resource(DL_CX, DL_CY, "CUCHILLO", td2, both_blocked)

    # Meseros
    dl_draw_mesero(td1, DL_M1X, DL_M1Y, THREAD_COLORS[0])
    dl_draw_mesero(td2, DL_M2X, DL_M2Y, THREAD_COLORS[1])

    # Flechas
    if td1["has"] == "tenedor":
        c = THREAD_COLORS[0]; stroke(c[0], c[1], c[2], 200); strokeWeight(2)
        line(DL_M1X + 25, DL_M1Y - 12, DL_TX - 38, DL_TY + 10)
    if td1["blocked"]:
        if both_blocked:
            pulse = abs(sin(pulse_timer * 0.1))
            stroke(255, int(50 * pulse), int(50 * pulse), 200)
        else:
            stroke(255, 100, 100, 180)
        strokeWeight(1.5)
        dl_dashed_line(DL_M1X + 25, DL_M1Y - 12, DL_CX - 38, DL_CY + 10)
    if td2["has"] == "cuchillo":
        c = THREAD_COLORS[1]; stroke(c[0], c[1], c[2], 200); strokeWeight(2)
        line(DL_M2X - 25, DL_M2Y - 12, DL_CX + 38, DL_CY + 10)
    if td2["blocked"]:
        if both_blocked:
            pulse = abs(sin(pulse_timer * 0.1))
            stroke(255, int(50 * pulse), int(50 * pulse), 200)
        else:
            stroke(255, 100, 100, 180)
        strokeWeight(1.5)
        dl_dashed_line(DL_M2X - 25, DL_M2Y - 12, DL_TX + 38, DL_TY + 10)

    if both_blocked:
        pulse = abs(sin(pulse_timer * 0.08))
        alpha = int(180 + 75 * pulse)
        fill(200, 40, 40, alpha); noStroke(); rect(190, 430, 380, 55, 10)
        fill(255); textSize(20); textAlign(CENTER)
        text("!! DEADLOCK !!", width / 2, 457)
        fill(255, 220, 80); textSize(10); textAlign(CENTER)
        text("Ninguno suelta su utensilio. Ambos esperan eternamente.", width / 2, 474)

    draw_bottom_hint(dl_running,
        "Deadlock = bloqueo circular eterno. Solucion: mismo orden de adquisicion de recursos.")

def dl_draw_resource(rx, ry, nombre, owner, both_blocked):
    has_it = owner["has"] == nombre.lower()
    if both_blocked:
        pulse = abs(sin(pulse_timer * 0.08))
        col = color(int(220 + 35 * pulse), 60, 60)
    elif has_it:
        c = THREAD_COLORS[owner["id"]]; col = color(c[0], c[1], c[2])
    else:
        col = color(140, 100, 50)
    stroke(col); strokeWeight(2); fill(40, 25, 10)
    rect(rx - 42, ry - 36, 84, 72, 8)
    fill(col); noStroke(); textSize(20); textAlign(CENTER)
    text("Y" if nombre == "TENEDOR" else "I", rx, ry + 2)
    fill(col); textSize(10); textAlign(CENTER)
    text(nombre, rx, ry + 26)
    if has_it:
        c = THREAD_COLORS[owner["id"]]
        fill(c[0], c[1], c[2]); noStroke(); rect(rx - 28, ry + 36, 56, 17, 4)
        fill(255); textSize(9); textAlign(CENTER)
        text("M{} lo tiene".format(owner["id"] + 1), rx, ry + 48)
    else:
        fill(80, 60, 30); noStroke(); rect(rx - 28, ry + 36, 56, 17, 4)
        fill(160, 130, 80); textSize(9); textAlign(CENTER)
        text("LIBRE", rx, ry + 48)

def dl_draw_mesero(td, mx, my, c):
    blocked = td["blocked"]; done = td["done"]
    fill(0, 0, 0, 60); noStroke(); ellipse(mx + 3, my + 3, 52, 52)
    if done: fill(c[0], c[1], c[2], 120); stroke(200, 200, 200, 100)
    elif blocked: fill(200, 60, 60); stroke(255, 100, 100)
    else: fill(c[0], c[1], c[2]); stroke(255, 255, 255)
    strokeWeight(2); ellipse(mx, my, 50, 50)
    fill(255); noStroke(); textSize(13); textAlign(CENTER)
    text("M{}".format(td["id"] + 1), mx, my + 5)
    fill(230, 200, 150); textSize(10); textAlign(CENTER); noStroke()
    text("Mesero {}".format(td["id"] + 1), mx, my + 36)
    state = td["state"]
    fill(255, 80, 80) if ("ESPERA" in state or blocked) else (fill(100, 220, 100) if done else fill(255, 200, 50))
    textSize(9); textAlign(CENTER)
    text(state, mx, my + 50)
    if td["has"] != "":
        fill(255, 200, 80); textSize(9); textAlign(CENTER)
        text("Tiene: " + td["has"].upper(), mx, my + 63)
    if blocked:
        fill(255, 60, 60); noStroke(); textSize(22); textAlign(CENTER)
        text("X", mx, my - 32)

def dl_dashed_line(x1, y1, x2, y2):
    steps = 12
    for i in range(steps):
        if i % 2 == 0:
            px1 = x1 + (x2 - x1) * i / float(steps)
            py1 = y1 + (y2 - y1) * i / float(steps)
            px2 = x1 + (x2 - x1) * (i + 1) / float(steps)
            py2 = y1 + (y2 - y1) * (i + 1) / float(steps)
            line(px1, py1, px2, py2)

# ================================================================
# DRAW MODO 5: MONITOR
# ================================================================
MON_ZX = 250; MON_ZY = 85; MON_ZW = 260; MON_ZH = 230

def draw_monitor():
    fill(255, 220, 50); textSize(16); textAlign(CENTER); noStroke()
    text("MONITOR - Restaurante", width / 2, 42)
    fill(200, 170, 130); textSize(10); textAlign(CENTER)
    text("El jefe de cocina coordina el acceso. Los meseros esperan su senal para entrar.", width / 2, 58)

    with data_lock:
        snap = list(mon_thread_data)

    ocupado, historial = monitor_obj.get_estado()
    slots_free = monitor_obj.capacidad - ocupado

    # Zona del monitor (cocina con jefe)
    fill(0, 0, 0, 80); noStroke(); rect(MON_ZX + 4, MON_ZY + 4, MON_ZW, MON_ZH, 10)
    stroke(200, 160, 80); strokeWeight(2); fill(50, 30, 12)
    rect(MON_ZX, MON_ZY, MON_ZW, MON_ZH, 10)

    fill(200, 160, 80); noStroke()
    rect(MON_ZX + 20, MON_ZY - 20, MON_ZW - 40, 28, 4)
    fill(30, 15, 5); textSize(11); textAlign(CENTER)
    text("COCINA CON MONITOR (Jefe)", MON_ZX + MON_ZW / 2, MON_ZY - 2)

    # Jefe de cocina (el monitor en si)
    jx = int(MON_ZX + MON_ZW / 2); jy = MON_ZY + 50
    fill(255, 200, 50, 60); noStroke(); ellipse(jx, jy, 90, 90)
    fill(255, 200, 50); stroke(255, 255, 255); strokeWeight(2)
    ellipse(jx, jy, 46, 46)
    fill(30, 15, 5); noStroke(); textSize(11); textAlign(CENTER)
    text("JEFE", jx, jy + 4)
    fill(230, 200, 150); textSize(9); textAlign(CENTER); noStroke()
    text("Monitor", jx, jy + 30)

    # Contador de capacidad
    fill(30, 20, 8); noStroke()
    rect(MON_ZX + 15, MON_ZY + 90, MON_ZW - 30, 45, 6)
    fill(200, 170, 100); textSize(10); textAlign(CENTER)
    text("Capacidad disponible", MON_ZX + MON_ZW / 2, MON_ZY + 110)
    mon_col = color(80, 220, 100) if slots_free > 0 else color(255, 70, 70)
    fill(mon_col); textSize(22); textAlign(CENTER)
    text("{} / {}".format(slots_free, monitor_obj.capacidad), MON_ZX + MON_ZW / 2, MON_ZY + 128)

    # Meseros dentro
    inside = [t for t in snap if t["inside"]]
    for idx, t in enumerate(inside):
        c = THREAD_COLORS[t["id"]]
        ix = int(MON_ZX + 55 + idx * 90); iy = MON_ZY + 180
        fill(c[0], c[1], c[2], 50); noStroke(); ellipse(ix, iy, 60, 60)
        fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(1.5)
        ellipse(ix, iy, 36, 36)
        fill(255); noStroke(); textSize(10); textAlign(CENTER)
        text("M{}".format(t["id"] + 1), ix, iy + 4)
        fill(40, 25, 10); noStroke()
        rect(ix - 24, iy + 22, 48, 8, 3)
        pw = int(48 * t["progress"] / 100.0)
        if pw > 0:
            fill(c[0], c[1], c[2]); rect(ix - 24, iy + 22, pw, 8, 3)

    if not inside:
        fill(100, 75, 40); textSize(11); textAlign(CENTER); noStroke()
        text("COCINA LIBRE", MON_ZX + MON_ZW / 2, MON_ZY + 185)

    # Historial del monitor (log de eventos)
    fill(20, 12, 5); noStroke()
    rect(MON_ZX, MON_ZY + MON_ZH + 10, MON_ZW, 110, 6)
    stroke(140, 100, 50); strokeWeight(1); noFill()
    rect(MON_ZX, MON_ZY + MON_ZH + 10, MON_ZW, 110, 6)
    fill(180, 140, 80); noStroke(); textSize(10); textAlign(LEFT)
    text("Log del Monitor:", MON_ZX + 8, MON_ZY + MON_ZH + 26)
    for idx, entry in enumerate(historial):
        fill(140, 200, 140) if "entro" in entry else fill(200, 140, 140)
        textSize(9); textAlign(LEFT)
        text(entry, MON_ZX + 8, MON_ZY + MON_ZH + 42 + idx * 13)

    # Fila izquierda
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(CENTER)
    text("EN ESPERA", 105, MON_ZY + 18)
    waiting = [t for t in snap if t["state"] == "PIDIENDO PERMISO"]
    for idx, t in enumerate(waiting):
        c = THREAD_COLORS[t["id"]]
        wx = 105; wy = MON_ZY + 46 + idx * 46
        fill(c[0], c[1], c[2]); stroke(255, 255, 255); strokeWeight(1.5)
        ellipse(wx, wy, 32, 32)
        fill(255); noStroke(); textSize(10); textAlign(CENTER)
        text("M{}".format(t["id"] + 1), wx, wy + 4)
        stroke(c[0], c[1], c[2], 140); strokeWeight(1.2)
        line(wx + 16, wy, MON_ZX - 2, MON_ZY + MON_ZH / 2)

    # Lista derecha
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(LEFT)
    text("MESEROS", 548, MON_ZY + 18)
    for t in snap:
        tid = t["id"]; c = THREAD_COLORS[tid]
        ty = MON_ZY + 35 + tid * 46
        fill(c[0], c[1], c[2], 100 if t["done"] else 255); noStroke()
        ellipse(558, ty, 26, 26)
        fill(255) if not t["done"] else fill(160, 160, 160)
        textSize(9); textAlign(CENTER)
        text("M{}".format(tid + 1), 558, ty + 4)
        state = t["state"]
        if state == "LISTO": fill(100, 220, 100)
        elif state == "COCINANDO": fill(255, 200, 50)
        elif state == "PIDIENDO PERMISO": fill(200, 140, 60)
        else: fill(160, 140, 110)
        textSize(9); textAlign(LEFT); noStroke()
        text(state, 573, ty + 4)

    if mon_finished:
        fill(30, 60, 30, 220); noStroke(); rect(40, 490, 680, 38, 10)
        fill(80, 220, 120); textSize(11); textAlign(CENTER)
        text("Todos los meseros atendidos. El monitor coordino el acceso con condiciones de espera.", width / 2, 514)

    draw_bottom_hint(mon_running,
        "Monitor = jefe que coordina. Usa condition.wait() y notify() internamente.")

# ================================================================
# DRAW MODO 6: RECURSOS COMPARTIDOS + CONCURRENCIA
# ================================================================
REC_ZY = 75
REC_RX = [140, 380, 620]
REC_RY = 160

def draw_rec():
    fill(255, 220, 50); textSize(16); textAlign(CENTER); noStroke()
    text("RECURSOS COMPARTIDOS + CONCURRENCIA", width / 2, 42)
    fill(200, 170, 130); textSize(10); textAlign(CENTER)
    text("Meseros comparten caja, bodega e impresora. Varios trabajan al mismo tiempo.", width / 2, 58)

    with data_lock:
        snap_t = list(rec_thread_data)
        snap_r = list(rec_resource_data)

    if len(snap_r) == 0:
        fill(160, 140, 110); textSize(13); textAlign(CENTER)
        text("Presiona [ESPACIO] para iniciar", width / 2, 300)
        draw_bottom_hint(False, "Concurrencia = varios hilos activos. Sincronizacion = acceso ordenado a recursos.")
        return

    # Dibuja los 3 recursos
    for rid in range(3):
        rd = snap_r[rid]
        rx = REC_RX[rid]; ry = REC_RY
        rc_col = REC_COLORS[rid]

        # Caja del recurso
        user_id = rd["user"]
        if rd["busy"] and user_id >= 0 and user_id < len(THREAD_COLORS):
            uc = THREAD_COLORS[user_id]
            stroke(uc[0], uc[1], uc[2]); strokeWeight(2)
            fill(uc[0], uc[1], uc[2], 40)
        else:
            stroke(rc_col[0], rc_col[1], rc_col[2]); strokeWeight(1.5)
            fill(40, 25, 10)
        rect(rx - 50, ry - 40, 100, 80, 8)

        fill(rc_col[0], rc_col[1], rc_col[2]); noStroke()
        textSize(12); textAlign(CENTER)
        text(REC_NAMES[rid], rx, ry - 14)

        user_id = rd["user"]
        if rd["busy"] and user_id >= 0 and user_id < len(THREAD_COLORS):
            uc = THREAD_COLORS[user_id]
            fill(uc[0], uc[1], uc[2]); textSize(10); textAlign(CENTER)
            text("M{} usando".format(user_id + 1), rx, ry + 8)
            fill(40, 25, 10); noStroke()
            rect(rx - 34, ry + 18, 68, 10, 3)
            # Busca progreso del usuario
            for t in snap_t:
                if t["using"] == rid:
                    pw = int(68 * t["progress"] / 100.0)
                    if pw > 0:
                        fill(uc[0], uc[1], uc[2])
                        rect(rx - 34, ry + 18, pw, 10, 3)
                    break
        else:
            fill(100, 80, 40); textSize(10); textAlign(CENTER)
            text("LIBRE", rx, ry + 10)

        # Etiqueta concepto
        fill(rc_col[0], rc_col[1], rc_col[2], 160)
        textSize(8); textAlign(CENTER)
        text("Recurso compartido", rx, ry + 35)

    # Etiqueta de concurrencia entre recursos
    fill(180, 180, 100); textSize(10); textAlign(CENTER); noStroke()
    text("< Varios meseros activos al mismo tiempo = CONCURRENCIA >", width / 2, REC_RY + 58)

    # Meseros (hilos)
    fill(180, 140, 80); noStroke(); textSize(11); textAlign(CENTER)
    text("MESEROS (Hilos)", width / 2, REC_RY + 82)

    col_w = int(width / REC_NUM)
    for t in snap_t:
        tid = t["id"]; c = THREAD_COLORS[tid % len(THREAD_COLORS)]
        tx = int(col_w * tid + col_w / 2)
        ty = REC_RY + 120

        # Linea hacia recurso que usa
        if t["using"] >= 0:
            rx2 = REC_RX[t["using"]]
            stroke(c[0], c[1], c[2], 180); strokeWeight(1.5)
            line(tx, ty - 18, rx2, REC_RY + 40)
        elif t["waiting_for"] >= 0:
            rx2 = REC_RX[t["waiting_for"]]
            stroke(255, 150, 50, 150); strokeWeight(1)
            dl_dashed_line(tx, ty - 18, rx2, REC_RY + 40)

        # Circulo mesero
        if t["done"]: fill(c[0], c[1], c[2], 100); stroke(200, 200, 200, 80)
        else: fill(c[0], c[1], c[2]); stroke(255, 255, 255)
        strokeWeight(1.5); ellipse(tx, ty, 34, 34)
        fill(255) if not t["done"] else fill(180, 180, 180)
        noStroke(); textSize(10); textAlign(CENTER)
        text("M{}".format(tid + 1), tx, ty + 4)

        # Estado
        state = t["state"]
        if "TERMINO" in state: fill(100, 220, 100)
        elif "USANDO" in state: fill(255, 200, 50)
        elif "ESPERANDO" in state: fill(200, 120, 60)
        else: fill(160, 140, 110)
        textSize(8); textAlign(CENTER); noStroke()
        # Corta el texto si es muy largo
        short_state = state.replace("ESPERANDO ", "ESP.").replace("USANDO ", "USA.")
        text(short_state, tx, ty + 24)

    # Panel de conceptos
    fill(20, 12, 5); noStroke()
    rect(30, 370, 700, 120, 8)
    stroke(120, 90, 40); strokeWeight(1); noFill()
    rect(30, 370, 700, 120, 8)

    concepts = [
        ("CONCURRENCIA",    "Varios meseros trabajan al mismo tiempo"),
        ("SINCRONIZACION",  "Los locks evitan que dos meseros usen el mismo recurso"),
        ("EXCLUSION MUTUA", "Solo 1 mesero por recurso a la vez"),
        ("RECURSOS COMP.",  "Caja, bodega e impresora son compartidos por todos"),
        ("HILOS",           "Cada mesero es un hilo independiente"),
    ]
    for idx, (concept, desc) in enumerate(concepts):
        col_idx = idx % len(THREAD_COLORS)
        c = THREAD_COLORS[col_idx]
        cx2 = 48 + (idx % 3) * 240
        cy2 = 388 + int(idx / 3) * 52
        fill(c[0], c[1], c[2]); noStroke(); textSize(10); textAlign(LEFT)
        text(concept + ":", cx2, cy2)
        fill(180, 160, 120); textSize(9); textAlign(LEFT)
        text(desc, cx2, cy2 + 14)

    if rec_finished:
        fill(30, 60, 30, 220); noStroke(); rect(40, 500, 680, 38, 10)
        fill(80, 220, 120); textSize(11); textAlign(CENTER)
        text("Todos los meseros completaron su trabajo. Concurrencia y sincronizacion exitosas.", width / 2, 524)

    draw_bottom_hint(rec_running,
        "Concurrencia = varios hilos activos. Sincronizacion = acceso ordenado a recursos compartidos.")

# ================================================================
# HELPER: pie de pagina
# ================================================================
def draw_bottom_hint(is_running, leyenda):
    fill(120, 100, 70); textSize(10); textAlign(CENTER); noStroke()
    if not is_running:
        text("Presiona [ESPACIO] para iniciar   |   [R] para reiniciar   |   [0] Menu principal", width / 2, 558)
    else:
        text("[R] para reiniciar   |   [0] Menu principal", width / 2, 558)
    fill(140, 120, 90); textSize(9); textAlign(LEFT)
    text(leyenda, 30, 542)

# ================================================================
# TECLADO
# ================================================================
def keyPressed():
    global current_mode

    # Cambio de modo
    if key == '0':
        reset_all(); current_mode = 0; return
    if key == '1':
        reset_all(); current_mode = 1; return
    if key == '2':
        reset_all(); current_mode = 2; return
    if key == '3':
        reset_all(); current_mode = 3; return
    if key == '4':
        reset_all(); current_mode = 4; return
    if key == '5':
        reset_all(); current_mode = 5; return
    if key == '6':
        reset_all(); current_mode = 6; return

    # Iniciar
    if key == ' ':
        if current_mode == 1 and not rc_running:   rc_start()
        elif current_mode == 2 and not sem_running: sem_start()
        elif current_mode == 3 and not mutex_running: mutex_start()
        elif current_mode == 4 and not dl_running:  dl_start()
        elif current_mode == 5 and not mon_running: mon_start()
        elif current_mode == 6 and not rec_running: rec_start()

    # Reiniciar
    if key == 'r' or key == 'R':
        if current_mode == 1:   rc_reset()
        elif current_mode == 2: sem_reset()
        elif current_mode == 3: mutex_reset()
        elif current_mode == 4: dl_reset()
        elif current_mode == 5: mon_reset()
        elif current_mode == 6: rec_reset()

def reset_all():
    rc_reset(); sem_reset(); mutex_reset()
    dl_reset(); mon_reset(); rec_reset()

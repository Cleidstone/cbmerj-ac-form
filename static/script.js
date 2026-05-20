// ── Fatores de cálculo (espelham calculator.py) ──────────────────────────
const FACTORS = {
  standard:      { area: 270.75, people: 270.75, appliances: 270.75, lamps: 15.39, window_morning: 270.75, window_afternoon: 361 },
  afternoon_sun: { area: 500,    people: 270.75, appliances: 270.75, lamps: 15.39, window_morning: 270.75, window_afternoon: 361 },
  large:         { area: 600,    people: 600,    appliances: 600,    lamps: 34.1,  window_morning: 600,    window_afternoon: 800  },
};
const STANDARD_SIZES = [12000, 18000, 36000, 60000];
const SIZE_LABELS = { 12000: 'Split 12k BTU/h', 18000: 'Split 18k BTU/h', 36000: 'Split 36k BTU/h', 60000: 'Split 60k BTU/h' };

let roomCount = 0;

// ── Verificar unidade ao selecionar no dropdown ───────────────────────────
document.getElementById('obm_select').addEventListener('change', function () {
  const code = this.value;
  if (!code) return;

  fetch('/check-unit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ obm_code: code }),
  })
    .then(r => r.json())
    .then(data => {
      const warn   = document.getElementById('already-submitted-warn');
      const body   = document.getElementById('unit-form-body');
      const premSec = document.getElementById('sec-premissas');
      const avancar = document.getElementById('btn-avancar-wrap');

      if (data.submitted) {
        warn.style.display   = 'block';
        body.style.display   = 'none';
        premSec.style.display = 'none';
        avancar.style.display = 'none';
      } else {
        warn.style.display   = 'none';
        body.style.display   = 'block';
        premSec.style.display = 'block';
        avancar.style.display = 'block';
      }
    });
});

// ── Avançar para o formulário principal ──────────────────────────────────
function avancar() {
  const code = document.getElementById('obm_select').value;
  const name = document.getElementById('commander_name').value.trim();
  const p1   = document.getElementById('prem1').checked;
  const p2   = document.getElementById('prem2').checked;
  const p3   = document.getElementById('prem3').checked;

  if (!code) { alert('Selecione sua Unidade (OBM).'); return; }
  if (!name) { alert('Informe o nome do responsável.'); return; }
  if (!p1 || !p2 || !p3) { alert('Confirme todas as premissas do cálculo antes de prosseguir.'); return; }

  // Copiar valores para hidden inputs do form
  document.getElementById('obm_code_hidden').value  = code;
  document.getElementById('obm_name_hidden').value  = document.getElementById('obm_select').options[document.getElementById('obm_select').selectedIndex].text;
  document.getElementById('commander_name_h').value = name;
  document.getElementById('contact_email_h').value  = document.getElementById('contact_email').value;
  document.getElementById('contact_phone_h').value  = document.getElementById('contact_phone').value;

  document.getElementById('sec-unidade').style.display   = 'none';
  document.getElementById('sec-premissas').style.display = 'none';
  document.getElementById('btn-avancar-wrap').style.display = 'none';
  document.getElementById('main-form').style.display     = 'block';

  if (roomCount === 0) addRoom();
}

// ── Adicionar ambiente ────────────────────────────────────────────────────
function addRoom() {
  const tpl = document.getElementById('room-template').innerHTML;
  const idx  = roomCount;
  const num  = roomCount + 1;
  const html = tpl.replaceAll('__IDX__', idx).replaceAll('__NUM__', num);

  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  document.getElementById('rooms-container').appendChild(wrapper.firstElementChild);

  roomCount++;
  document.getElementById('room_count').value = roomCount;
}

// ── Remover ambiente ──────────────────────────────────────────────────────
function removeRoom(btn) {
  if (document.querySelectorAll('.room-card').length <= 1) {
    alert('É necessário pelo menos um ambiente.'); return;
  }
  btn.closest('.room-card').remove();
  renumberRooms();
}

function renumberRooms() {
  document.querySelectorAll('.room-card').forEach((card, i) => {
    card.querySelector('.room-num').textContent = i + 1;
  });
}

// ── Calcular BTU de um ambiente ───────────────────────────────────────────
function calcRoom(card) {
  const idx   = card.dataset.roomIndex;
  const rtype = card.querySelector(`[name="room_${idx}_type"]`).value;
  const f     = FACTORS[rtype] || FACTORS.standard;

  const length   = parseFloat(card.querySelector(`[name="room_${idx}_length"]`)?.value) || 0;
  const width    = parseFloat(card.querySelector(`[name="room_${idx}_width"]`)?.value)  || 0;
  const area     = parseFloat((length * width).toFixed(2));
  const people   = parseInt(card.querySelector(`[name="room_${idx}_people"]`)?.value)      || 0;
  const appl     = parseInt(card.querySelector(`[name="room_${idx}_appliances"]`)?.value)  || 0;
  const lamps    = parseInt(card.querySelector(`[name="room_${idx}_lamps"]`)?.value)       || 0;
  const winM     = card.querySelector(`[name="room_${idx}_window_morning"]`)?.checked ? 1 : 0;
  const winA     = card.querySelector(`[name="room_${idx}_window_afternoon"]`)?.checked ? 1 : 0;

  // Mostrar área calculada
  const areaDiv = card.querySelector('.area-display');
  if (area > 0) {
    card.querySelector('.area-value').textContent = `${area.toFixed(2)} m²`;
    areaDiv.style.display = 'block';
  }

  if (area <= 0) return;

  const btu = area * f.area + people * f.people + appl * f.appliances +
              lamps * f.lamps + winM * f.window_morning + winA * f.window_afternoon;

  const recSize = recommendSize(btu);
  const recQty  = btu > 60000 ? Math.ceil(btu / 60000) : 1;

  // Mostrar resultado
  const calcDiv = card.querySelector('.calc-result');
  calcDiv.style.display = 'flex';
  card.querySelector('.btu-value').textContent = formatBTU(btu) + ' BTU/h';
  card.querySelector('.rec-value').textContent = `${recQty}× ${SIZE_LABELS[recSize] || recSize + ' BTU/h'}`;

  // Mostrar seleção de equipamento
  const equipDiv = card.querySelector('.equip-select');
  equipDiv.style.display = 'block';

  // Pré-selecionar tamanho recomendado
  const sizeSelect = card.querySelector(`[name="room_${idx}_selected_size"]`);
  if (!sizeSelect._userChanged) sizeSelect.value = String(recSize);

  const qtyInput = card.querySelector(`[name="room_${idx}_selected_qty"]`);
  if (!qtyInput._userChanged) qtyInput.value = recQty;
}

function recommendSize(btu) {
  for (const s of STANDARD_SIZES) { if (btu <= s) return s; }
  return 60000;
}

function formatBTU(v) {
  return Math.round(v).toLocaleString('pt-BR');
}

// ── Mudança no select de tamanho ──────────────────────────────────────────
function onSizeChange(select) {
  select._userChanged = true;
  const card = select.closest('.room-card');
  const isCustom = select.value === 'custom';
  card.querySelector('.custom-size-row').style.display   = isCustom ? 'block' : 'none';
  card.querySelector('.justificativa-row').style.display = isCustom ? 'block' : 'none';

  if (!isCustom) {
    const recVal = card.querySelector('.rec-value').textContent;
    const selBTU = parseInt(select.value);
    const recBTU = STANDARD_SIZES.find(s =>
      recVal.includes(SIZE_LABELS[s]?.replace('BTU/h', '').trim())
    );
    const isDiff = recBTU && selBTU !== recBTU;
    card.querySelector('.justificativa-row').style.display = isDiff ? 'block' : 'none';
  }
}

// ── Validação antes do envio ──────────────────────────────────────────────
document.getElementById('main-form')?.addEventListener('submit', function (e) {
  const cards = document.querySelectorAll('.room-card');
  if (cards.length === 0) {
    e.preventDefault(); alert('Adicione pelo menos um ambiente.'); return;
  }

  let ok = true;
  cards.forEach(card => {
    const idx  = card.dataset.roomIndex;
    const name = card.querySelector(`[name="room_${idx}_name"]`)?.value.trim();
    const len  = parseFloat(card.querySelector(`[name="room_${idx}_length"]`)?.value);
    const wid  = parseFloat(card.querySelector(`[name="room_${idx}_width"]`)?.value);
    const size = card.querySelector(`[name="room_${idx}_selected_size"]`)?.value;
    const jrow = card.querySelector('.justificativa-row');
    const just = card.querySelector(`[name="room_${idx}_justification"]`)?.value.trim();

    if (!name || !len || !wid) { ok = false; }
    if (jrow?.style.display !== 'none' && !just) { ok = false; }

    // Se custom, transferir valor numérico para hidden
    if (size === 'custom') {
      const customVal = card.querySelector(`[name="room_${idx}_custom_size"]`)?.value;
      if (!customVal) { ok = false; }
      else {
        const hidden = document.createElement('input');
        hidden.type  = 'hidden';
        hidden.name  = `room_${idx}_selected_size`;
        hidden.value = customVal;
        card.querySelector(`[name="room_${idx}_selected_size"]`).name = `_room_${idx}_selected_size_old`;
        card.appendChild(hidden);
      }
    }
  });

  if (!ok) {
    e.preventDefault();
    alert('Preencha todos os campos obrigatórios e justifique os equipamentos fora do padrão BM4.');
  }
});

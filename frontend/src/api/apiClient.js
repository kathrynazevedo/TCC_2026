const API_URL = 'http://localhost:3000/api';

export async function getViolations() {
  try {
    const response = await fetch(`${API_URL}/violations`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Erro ao buscar dados do servidor');
         
    const json = await response.json();
    return json.data;
  } catch (error) {
    console.error("Erro na comunicação com a API:", error);
    return [];
  }
}

export async function updateViolationStatus(id, newStatus) {
  const response = await fetch(`${API_URL}/violations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  });
  if (!response.ok) throw new Error('Erro ao atualizar status');
  return response.json();
}

export async function getMetrics() {
  try {
    const response = await fetch(`${API_URL}/metrics`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Erro ao buscar métricas');
    return response.json();
  } catch (error) {
    console.error("Erro ao buscar métricas:", error);
    return null;
  }
}

  export async function getAreas() {
  try {
    const response = await fetch(`${API_URL}/areas`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Erro ao buscar áreas');
    const json = await response.json();
    return json.data;
    } catch (error) {
    console.error("Erro ao buscar áreas:", error);
    return [];
    }
}
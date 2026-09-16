const API_URL = 'http://localhost:3000/api';

export async function getViolations() {
  try {
    // A mágica acontece aqui: 'no-store' proíbe o navegador de usar a memória cache
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
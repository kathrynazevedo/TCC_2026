// Padrão "/api": em dev o Vite repassa ao backend; em produção o próprio backend serve o front.
const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { cache: 'no-store', ...options });
  } catch {
    throw new Error('Não foi possível conectar ao servidor. Verifique se a API está em execução.');
  }

  if (!response.ok) {
    let message = `Erro ${response.status} ao falar com o servidor.`;
    try {
      const body = await response.json();
      if (body && body.error) message = body.error;
    } catch {
      // resposta sem JSON: mantém a mensagem genérica
    }
    throw new Error(message);
  }
  return response.json();
}

export const getViolations = async () => (await request('/violations')).data;

export const updateViolationStatus = (id, status) =>
  request(`/violations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });

export const getMetrics = () => request('/metrics');

export const getAreas = async () => (await request('/areas')).data;

export const getWorkers = async () => (await request('/workers')).data;

export const getEdgeStatus = () => request('/status/edge');

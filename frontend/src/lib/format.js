import { format, formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

const toDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

export const formatDateTime = (value, pattern = "dd/MM/yy HH:mm") => {
  const date = toDate(value);
  return date ? format(date, pattern, { locale: ptBR }) : "-";
};

export const timeAgo = (value) => {
  const date = toDate(value);
  return date ? formatDistanceToNow(date, { addSuffix: true, locale: ptBR }) : "-";
};

export const initials = (name = "") =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

// "Renan Albuquerque Nunes" -> "Renan N."
export const shortName = (name = "") => {
  const parts = name.split(" ").filter(Boolean);
  return parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1][0]}.` : name;
};

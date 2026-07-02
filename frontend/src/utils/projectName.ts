/**
 * Client-side project name validation. Mirrors the backend rules in
 * `backend/src/projects/views/schemas/project.py`: at most 30 characters and
 * only letters, numbers, spaces, '_', '-' and ':'.
 */

export const PROJECT_NAME_MAX_LENGTH = 30;

const PROJECT_NAME_PATTERN = /^[a-zA-Z0-9_\-: ]+$/;

/**
 * Returns an error message when `name` is invalid, or `null` when it is valid.
 */
export function validateProjectName(name: string): string | null {
  if (!name.trim()) {
    return "O nome não pode estar vazio.";
  }
  if (name.length > PROJECT_NAME_MAX_LENGTH) {
    return `O nome não pode ter mais de ${PROJECT_NAME_MAX_LENGTH} caracteres.`;
  }
  if (!PROJECT_NAME_PATTERN.test(name)) {
    return "O nome só pode conter letras, números, espaços, '_', '-' e ':'.";
  }
  return null;
}

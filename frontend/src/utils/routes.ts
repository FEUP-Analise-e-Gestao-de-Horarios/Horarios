type ExtractParams<P extends string> = P extends `${string}:${infer Param}/${infer Rest}`
  ? Param | ExtractParams<`/${Rest}`>
  : P extends `${string}:${infer Param}`
    ? Param
    : never;

export function buildPath<P extends string>(
  template: P,
  params: Record<ExtractParams<P>, string>,
): string {
  let result: string = template;
  for (const [key, value] of Object.entries(params as Record<string, string>)) {
    result = result.replace(`:${key}`, value);
  }
  return result;
}

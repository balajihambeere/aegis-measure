import nextConfig from "eslint-config-next";

const eslintConfig = [
  ...nextConfig,
  {
    ignores: [".next/**", "node_modules/**"],
  },
  {
    rules: {
      // This dashboard is a plain client-rendered app with no server-side
      // data layer (no Suspense/use()) — "fetch on mount" via useEffect is
      // the deliberate, standard pattern here, not an accidental misuse.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default eslintConfig;

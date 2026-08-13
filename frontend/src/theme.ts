import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#4f8cc9" },
    background: { default: "#14181d", paper: "#1b2129" },
  },
  typography: {
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    fontSize: 13,
  },
  components: {
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600 } },
    },
  },
});

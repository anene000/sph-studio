import type { ReactNode } from "react";

export const metadata = {
  title: "SPH Studio",
  description: "GUI for the Taichi SPH fluid/rigid simulator",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body
        style={{
          margin: 0,
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif",
          background: "#0b0e14",
          color: "#e6e6e6",
        }}
      >
        {children}
      </body>
    </html>
  );
}

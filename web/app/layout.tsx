import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"TrustDesk | Support operations",description:"Evidence-led AI support with human oversight"};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>}

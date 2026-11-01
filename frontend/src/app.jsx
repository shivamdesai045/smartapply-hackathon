import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import Header from "./components/Header";
import HeroSearch from "./components/HeroSearch";
import StatsBar from "./components/StatsBar";
import ServicesPreview from "./components/ServicesPreview";
import ChatBot from "./components/ChatBot";
import LoginRequiredModal from "./components/LoginRequiredModal";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Services from "./pages/Services";
import Checklist from "./pages/Checklist";
import About from "./pages/About";
import MyDocuments from "./pages/MyDocuments";
import VerificationReport from "./pages/VerificationReport";

function Home() {
  return (
    <>
      <HeroSearch />
      <StatsBar />
      <ServicesPreview />
    </>
  );
}

function AppShell() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col justify-between">
      <div>
        {!isHome && <Header />}
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/services" element={<Services />} />
            <Route path="/about" element={<About />} />
            <Route path="/checklist/:slug" element={<Checklist />} />
            <Route path="/my-documents" element={<MyDocuments />} />
            <Route path="/report/:slug" element={<VerificationReport />} />
          </Routes>
        </main>
      </div>

      <ChatBot />
      <LoginRequiredModal />
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

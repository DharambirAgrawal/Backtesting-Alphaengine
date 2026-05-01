"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  TrendingUp,
  Zap,
  Brain,
  BarChart3,
  ArrowRight,
  Check,
  Mail,
} from "lucide-react";

export default function LandingPage() {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    // TODO: Add API call to save email to waitlist
    console.log("Email submitted:", email);
    setSubscribed(true);
    setEmail("");

    setTimeout(() => setSubscribed(false), 3000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <span className="font-semibold text-white text-lg">AlphaEngine</span>
          </div>
          <div className="flex gap-3">
            <Button variant="ghost" className="text-slate-300 hover:text-white" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600">
              <Link href="/login">Get Started</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl sm:text-6xl font-bold text-white leading-tight">
              Trade Smarter with{" "}
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                AI
              </span>
            </h1>
            <p className="text-xl text-slate-300 max-w-2xl mx-auto">
              An intelligent portfolio management platform that uses advanced AI agents to analyze
              markets and execute data-driven trading decisions in real-time.
            </p>
          </div>

          {/* CTA Section */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
            <Button asChild size="lg" className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white px-8">
              <Link href="/login">
                Start Trading Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" className="border-slate-700 text-white hover:bg-slate-800">
              <a href="#features">Learn More</a>
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 pt-12 border-t border-slate-800">
            <div>
              <div className="text-2xl font-bold text-white">2+</div>
              <p className="text-slate-400 text-sm">Active Portfolios</p>
            </div>
            <div>
              <div className="text-2xl font-bold text-white">49+</div>
              <p className="text-slate-400 text-sm">Tracked Trades</p>
            </div>
            <div>
              <div className="text-2xl font-bold text-white">Real-time</div>
              <p className="text-slate-400 text-sm">AI Analysis</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-6xl mx-auto">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-4xl font-bold text-white">Powerful Features</h2>
            <p className="text-slate-400">Everything you need for intelligent portfolio management</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Feature 1 */}
            <Card className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-slate-700 p-8 hover:border-slate-600 transition">
              <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-4">
                <Brain className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">AI-Powered Trading</h3>
              <p className="text-slate-400">
                Advanced AI agents analyze market trends, news, and technical indicators to make
                informed trading decisions automatically.
              </p>
            </Card>

            {/* Feature 2 */}
            <Card className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-slate-700 p-8 hover:border-slate-600 transition">
              <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Real-time Analytics</h3>
              <p className="text-slate-400">
                Track portfolio performance with interactive charts, detailed metrics, and
                comprehensive performance statistics.
              </p>
            </Card>

            {/* Feature 3 */}
            <Card className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-slate-700 p-8 hover:border-slate-600 transition">
              <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-pink-500 to-pink-600 flex items-center justify-center mb-4">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Automated Execution</h3>
              <p className="text-slate-400">
                Scheduled runs execute trades at optimal times with configurable parameters and
                full audit trails of all decisions.
              </p>
            </Card>

            {/* Feature 4 */}
            <Card className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-slate-700 p-8 hover:border-slate-600 transition">
              <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center mb-4">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Portfolio Management</h3>
              <p className="text-slate-400">
                Manage multiple portfolios, monitor holdings, analyze realized gains, and track
                trading performance all in one place.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">How It Works</h2>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Create Portfolio",
                description: "Set up your portfolio with initial capital and select the stocks you want to track.",
              },
              {
                step: "02",
                title: "AI Analysis",
                description: "Our agents analyze market data, news, and technical indicators 24/7.",
              },
              {
                step: "03",
                title: "Automated Trades",
                description: "Execute trades based on AI insights with full transparency and control.",
              },
            ].map((item, i) => (
              <div key={i} className="relative">
                {i < 2 && (
                  <div className="hidden md:block absolute top-12 -right-4 w-8 h-0.5 bg-gradient-to-r from-slate-700 to-transparent" />
                )}
                <div className="space-y-3">
                  <div className="text-3xl font-bold text-slate-400">{item.step}</div>
                  <h3 className="text-xl font-semibold text-white">{item.title}</h3>
                  <p className="text-slate-400">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h2 className="text-4xl font-bold text-white">Ready to Start?</h2>
            <p className="text-slate-300 text-lg">
              Join us and let AI power your trading decisions. Get started with a free demo portfolio today.
            </p>
          </div>

          <form onSubmit={handleRequestAccess} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <Input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
              required
            />
            <Button
              type="submit"
              className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
            >
              {subscribed ? <Check className="h-5 w-5" /> : <>Request Access <Mail className="ml-2 h-4 w-4" /></>}
            </Button>
          </form>

          {subscribed && (
            <div className="text-green-400 text-sm font-medium">
              ✓ Thanks! We'll be in touch soon.
            </div>
          )}

          <div className="pt-8 flex justify-center gap-6 text-slate-400 text-sm">
            <Link href="/login" className="hover:text-white transition">
              Sign In
            </Link>
            <Link href="/login" className="hover:text-white transition">
              Create Account
            </Link>
            <a href="#" className="hover:text-white transition">
              Documentation
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-400 text-sm">
          <p>&copy; 2026 AlphaEngine. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition">
              Privacy Policy
            </a>
            <a href="#" className="hover:text-white transition">
              Terms of Service
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

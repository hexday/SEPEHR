// SEPEHR Frontend — News Page

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { BottomNav } from "@/components/layout/BottomNav";
import { get } from "@/lib/api";
import type { NewsServer, NewsPost, NewsCategory } from "@/types";

export default function NewsPage() {
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);

  const { data: servers, isLoading: serversLoading } = useQuery({
    queryKey: ["news-servers"],
    queryFn: () => get<NewsServer[]>("/api/v1/news/servers"),
    staleTime: 5 * 60 * 1000,
  });

  const { data: categories } = useQuery({
    queryKey: ["news-categories", selectedServerId],
    queryFn: () =>
      get<NewsCategory[]>(`/api/v1/news/servers/${selectedServerId}/categories`),
    enabled: !!selectedServerId,
  });

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ["news-posts", selectedServerId, selectedCategoryId],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "30" });
      if (selectedServerId) params.set("server_id", selectedServerId);
      if (selectedCategoryId) params.set("category_id", selectedCategoryId);
      return get<NewsPost[]>(`/api/v1/news/posts?${params}`);
    },
    staleTime: 30000,
  });

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-bg/80 backdrop-blur-xl border-b border-border">
        <div className="px-4 pt-14 pb-3">
          <h1 className="text-xl font-semibold mb-3">اخبار</h1>

          {/* Server tabs */}
          <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1 -mx-4 px-4">
            <ServerTab
              label="همه"
              isActive={!selectedServerId}
              onClick={() => {
                setSelectedServerId(null);
                setSelectedCategoryId(null);
              }}
            />
            {servers?.map((s) => (
              <ServerTab
                key={s.id}
                label={s.name}
                isActive={selectedServerId === s.id}
                onClick={() => {
                  setSelectedServerId(s.id);
                  setSelectedCategoryId(null);
                }}
              />
            ))}
          </div>
        </div>

        {/* Category pills */}
        {categories && categories.length > 0 && (
          <div className="flex gap-2 overflow-x-auto scrollbar-hide px-4 pb-3">
            <CategoryPill
              label="همه"
              isActive={!selectedCategoryId}
              color={null}
              onClick={() => setSelectedCategoryId(null)}
            />
            {categories.map((cat) => (
              <CategoryPill
                key={cat.id}
                label={cat.name}
                isActive={selectedCategoryId === cat.id}
                color={cat.color}
                onClick={() => setSelectedCategoryId(cat.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Posts */}
      <div className="content-pb px-4 py-4">
        {postsLoading ? (
          <PostsSkeleton />
        ) : posts && posts.length > 0 ? (
          <div className="space-y-3">
            {posts.map((post, i) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <NewsPostCard post={post} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center pt-24 text-center px-8">
            <span className="text-4xl mb-4">📰</span>
            <h3 className="font-semibold mb-1">خبری وجود ندارد</h3>
            <p className="text-sm text-primary-subtle">
              در این بخش هنوز خبری منتشر نشده است
            </p>
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  );
}

function ServerTab({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
        isActive
          ? "bg-accent text-white shadow-glow"
          : "bg-bg-card text-primary-subtle border border-border"
      }`}
    >
      {label}
    </button>
  );
}

function CategoryPill({
  label,
  isActive,
  color,
  onClick,
}: {
  label: string;
  isActive: boolean;
  color: string | null;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-all border ${
        isActive
          ? "border-transparent text-white"
          : "border-border text-primary-subtle"
      }`}
      style={
        isActive && color
          ? { backgroundColor: color + "30", borderColor: color + "60", color }
          : isActive
          ? { backgroundColor: "#4F8CFF20", borderColor: "#4F8CFF40", color: "#4F8CFF" }
          : {}
      }
    >
      {label}
    </button>
  );
}

function NewsPostCard({ post }: { post: NewsPost }) {
  return (
    <Link href={`/news/${post.id}`}>
      <div className="glass-card overflow-hidden hover:bg-bg-elevated transition-colors">
        {post.cover_image_url && (
          <div className="h-44 overflow-hidden">
            <img
              src={post.cover_image_url}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        )}
        <div className="p-4">
          <h2 className="font-semibold text-base leading-snug mb-2">{post.title}</h2>
          {post.summary && (
            <p className="text-sm text-primary-subtle line-clamp-2 mb-3">
              {post.summary}
            </p>
          )}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {post.publisher && (
                <span className="text-xs text-primary-subtle">
                  {post.publisher.display_name}
                </span>
              )}
            </div>
            <span className="text-xs text-primary-subtle">
              {post.published_at
                ? formatDistanceToNow(new Date(post.published_at), { addSuffix: true })
                : ""}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function PostsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="glass-card overflow-hidden">
          <div className="h-40 shimmer" />
          <div className="p-4 space-y-2">
            <div className="h-4 w-3/4 rounded shimmer" />
            <div className="h-3 w-full rounded shimmer" />
            <div className="h-3 w-1/3 rounded shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}

"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { UserTable } from "@/components/admin/user-table";
import { UserModal } from "@/components/admin/user-modal";
import { useUsers } from "@/hooks/use-users";
import { useAuth } from "@/hooks/use-auth";
import { createUser, updateUser, deleteUser } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Loader2 } from "lucide-react";
import type { User } from "@/lib/types";

export default function AdminUsersPage() {
  const { users, isLoading, refresh } = useUsers();
  const { email } = useAuth();

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSaveUser = async (data: { email: string; password?: string }) => {
    if (editingUser) {
      // Update existing user
      await updateUser(editingUser.id, data);
      toast.success("User updated");
    } else {
      // Create new user
      if (!data.password) {
        throw new Error("Password is required");
      }
      await createUser(data.email, data.password);
      toast.success("User created");
    }
    refresh();
  };

  const handleDeleteUser = async () => {
    if (!deletingUser) return;

    setIsDeleting(true);
    try {
      await deleteUser(deletingUser.id);
      toast.success("User deleted");
      refresh();
    } catch {
      toast.error("Failed to delete user");
    } finally {
      setIsDeleting(false);
      setDeletingUser(null);
    }
  };

  const openCreateModal = () => {
    setEditingUser(null);
    setIsModalOpen(true);
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setIsModalOpen(true);
  };

  return (
    <DashboardLayout title="User Management">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              User Management
            </h1>
            <p className="text-muted-foreground">
              Manage user accounts and access
            </p>
          </div>
          <Button onClick={openCreateModal}>
            <Plus className="h-4 w-4" />
            Add User
          </Button>
        </div>

        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-base font-medium">
              Users
              {users.length > 0 && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  ({users.length} total)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <UserTable
              users={users}
              currentUserEmail={email}
              isLoading={isLoading}
              onEdit={openEditModal}
              onDelete={setDeletingUser}
            />
          </CardContent>
        </Card>
      </div>

      {/* Create/Edit Modal */}
      <UserModal
        user={editingUser}
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveUser}
      />

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!deletingUser}
        onOpenChange={(open) => !open && setDeletingUser(null)}
      >
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User?</AlertDialogTitle>
            <AlertDialogDescription>
              Delete {deletingUser?.email}? They will lose access immediately.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteUser}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  );
}

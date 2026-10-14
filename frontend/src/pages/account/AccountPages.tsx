import { zodResolver } from '@hookform/resolvers/zod';
import { Heart, MapPin, Monitor, Pencil, Plus, ShieldCheck, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router';
import type { z } from 'zod';

import {
  useAddresses,
  useChangePassword,
  useDeleteAddress,
  useLogout,
  useMe,
  useRevokeSession,
  useSaveAddress,
  useSessions,
  useUpdateProfile,
  type Address,
} from '@/api/queries/account';
import { useAccountWishlist } from '@/api/queries/wishlist';
import { AccountSection } from '@/components/account/AccountLayout';
import { AddressForm } from '@/components/account/AddressForm';
import { PageMeta } from '@/components/layout/Page';
import { ProductGrid } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { DialogClose, DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { Alert, Badge, EmptyState, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { formatDateTime } from '@/lib/format';
import { applyServerErrors, errorMessage } from '@/lib/forms';
import { changePasswordSchema, profileSchema } from '@/lib/validation/account';

export function AccountOverviewPage() {
  const me = useMe();
  const addresses = useAddresses();
  const user = me.data;
  if (!user) return null;
  const defaultAddress = addresses.data?.find((a) => a.is_default_shipping);
  const cards = [
    {
      to: '/account/profile',
      icon: Pencil,
      title: 'Profile',
      text: `${user.full_name} · ${user.email}`,
    },
    {
      to: '/account/addresses',
      icon: MapPin,
      title: 'Addresses',
      text: defaultAddress
        ? `${defaultAddress.city}, ${defaultAddress.pincode}`
        : 'Add an address for faster checkout',
    },
    { to: '/account/wishlist', icon: Heart, title: 'Wishlist', text: 'Pieces you have saved' },
    {
      to: '/account/security',
      icon: ShieldCheck,
      title: 'Sign-in & security',
      text: 'Password and signed-in devices',
    },
  ];
  return (
    <>
      <PageMeta title="My account" path="/account" noindex />
      <AccountSection title="Overview">
        <ul className="grid gap-4 sm:grid-cols-2">
          {cards.map(({ to, icon: Icon, title, text }) => (
            <li key={to}>
              <Link
                to={to}
                className="flex h-full items-start gap-4 rounded-md border border-line bg-surface p-5 transition-colors hover:border-ink/40"
              >
                <Icon className="mt-0.5 size-5 text-gold" strokeWidth={1.5} aria-hidden="true" />
                <span>
                  <span className="block font-medium">{title}</span>
                  <span className="mt-1 block text-sm text-ink-muted">{text}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-8 text-sm text-ink-muted">
          Order history will appear here once online ordering opens.
        </p>
      </AccountSection>
    </>
  );
}

export function ProfilePage() {
  const me = useMe();
  const update = useUpdateProfile();
  const { notify } = useToast();
  const user = me.data;
  const form = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    values: { full_name: user?.full_name ?? '', phone: user?.phone ?? '' },
  });
  const { errors } = form.formState;
  if (!user) return null;

  return (
    <>
      <PageMeta title="Profile" path="/account/profile" noindex />
      <AccountSection
        title="Profile"
        description="Your name and mobile number for orders and delivery."
      >
        <form
          noValidate
          className="max-w-lg space-y-5"
          onSubmit={form.handleSubmit((values) => {
            update.mutate(
              { full_name: values.full_name, phone: values.phone || null },
              {
                onSuccess: () => {
                  notify('Profile updated.');
                },
                onError: (error) => {
                  applyServerErrors(error, form.setError, ['full_name', 'phone']);
                },
              },
            );
          })}
        >
          {update.isError && <Alert tone="danger" title={errorMessage(update.error)} />}
          <FormField label="Email" hint="Contact us if you need to change your email address.">
            <Input value={user.email} readOnly disabled />
          </FormField>
          <FormField label="Full name" required error={errors.full_name?.message}>
            <Input autoComplete="name" {...form.register('full_name')} />
          </FormField>
          <FormField label="Mobile number" hint="Optional" error={errors.phone?.message}>
            <Input type="tel" inputMode="tel" autoComplete="tel" {...form.register('phone')} />
          </FormField>
          <Button type="submit" loading={update.isPending}>
            Save changes
          </Button>
        </form>
      </AccountSection>
    </>
  );
}

function AddressCard({
  address,
  onEdit,
  onDelete,
}: {
  address: Address;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <article className="flex h-full flex-col rounded-md border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center gap-2">
        {address.label && <p className="font-medium">{address.label}</p>}
        {address.is_default_shipping && <Badge tone="gold">Default delivery</Badge>}
        {address.is_default_billing && <Badge>Default billing</Badge>}
      </div>
      <address className="mt-3 flex-1 text-sm leading-relaxed text-ink-muted not-italic">
        <span className="text-ink">{address.full_name}</span>
        <br />
        {address.line1}
        {address.line2 && (
          <>
            <br />
            {address.line2}
          </>
        )}
        {address.landmark && (
          <>
            <br />
            Near {address.landmark}
          </>
        )}
        <br />
        {address.city}, {address.state} {address.pincode}
        <br />
        {address.phone}
      </address>
      <div className="mt-4 flex gap-2">
        <Button variant="secondary" size="sm" onClick={onEdit}>
          <Pencil className="size-3.5" aria-hidden="true" /> Edit
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          aria-label={`Delete address ${address.line1}`}
        >
          <Trash2 className="size-3.5" aria-hidden="true" /> Delete
        </Button>
      </div>
    </article>
  );
}

export function AddressesPage() {
  const addresses = useAddresses();
  const save = useSaveAddress();
  const remove = useDeleteAddress();
  const { notify } = useToast();
  const [editing, setEditing] = useState<Address | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Address | null>(null);

  const closeEditor = () => {
    setEditing(null);
    save.reset();
  };

  return (
    <>
      <PageMeta title="Addresses" path="/account/addresses" noindex />
      <AccountSection
        title="Addresses"
        description="Saved addresses make checkout faster."
        action={
          <Button
            size="sm"
            onClick={() => {
              setEditing('new');
            }}
          >
            <Plus className="size-4" aria-hidden="true" /> Add address
          </Button>
        }
      >
        {addresses.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </div>
        ) : addresses.isError ? (
          <ErrorState error={addresses.error} onRetry={() => void addresses.refetch()} />
        ) : addresses.data.length === 0 ? (
          <EmptyState
            icon={MapPin}
            title="No saved addresses"
            action={
              <Button
                onClick={() => {
                  setEditing('new');
                }}
              >
                Add your first address
              </Button>
            }
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {addresses.data.map((address) => (
              <li key={address.id}>
                <AddressCard
                  address={address}
                  onEdit={() => {
                    setEditing(address);
                  }}
                  onDelete={() => {
                    setDeleting(address);
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </AccountSection>

      <DialogRoot
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) closeEditor();
        }}
      >
        {editing !== null && (
          <DialogContent
            title={editing === 'new' ? 'Add an address' : 'Edit address'}
            className="max-w-2xl"
          >
            <AddressForm
              address={editing === 'new' ? undefined : editing}
              submitting={save.isPending}
              error={save.error}
              onSubmit={(body) => {
                save.mutate(
                  { id: editing === 'new' ? undefined : editing.id, body },
                  {
                    onSuccess: () => {
                      notify('Address saved.');
                      closeEditor();
                    },
                  },
                );
              }}
            />
          </DialogContent>
        )}
      </DialogRoot>

      <DialogRoot
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
      >
        {deleting && (
          <DialogContent
            title="Delete this address?"
            description={`${deleting.line1}, ${deleting.city}`}
          >
            {remove.isError && (
              <Alert tone="danger" title={errorMessage(remove.error)} className="mb-4" />
            )}
            <div className="flex justify-end gap-3">
              <DialogClose asChild>
                <Button variant="secondary">Keep it</Button>
              </DialogClose>
              <Button
                variant="danger"
                loading={remove.isPending}
                onClick={() => {
                  remove.mutate(deleting.id, {
                    onSuccess: () => {
                      notify('Address deleted.', 'info');
                      setDeleting(null);
                    },
                  });
                }}
              >
                Delete address
              </Button>
            </div>
          </DialogContent>
        )}
      </DialogRoot>
    </>
  );
}

export function AccountWishlistPage() {
  const wishlist = useAccountWishlist(true);
  return (
    <>
      <PageMeta title="Wishlist" path="/account/wishlist" noindex />
      <AccountSection
        title="Wishlist"
        description="Current prices and availability of the pieces you saved."
      >
        {wishlist.isError ? (
          <ErrorState error={wishlist.error} onRetry={() => void wishlist.refetch()} />
        ) : wishlist.data && wishlist.data.length === 0 ? (
          <EmptyState
            icon={Heart}
            title="Nothing saved yet"
            action={
              <Button asChild>
                <Link to="/collections">Explore the collection</Link>
              </Button>
            }
          >
            Tap the heart on any piece to keep it here.
          </EmptyState>
        ) : (
          <ProductGrid
            products={wishlist.data}
            loading={wishlist.isPending}
            skeletonCount={3}
            className="xl:grid-cols-3"
          />
        )}
      </AccountSection>
    </>
  );
}

function ChangePasswordForm() {
  const change = useChangePassword();
  const { notify } = useToast();
  const form = useForm<z.infer<typeof changePasswordSchema>>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  });
  const { errors } = form.formState;
  return (
    <form
      noValidate
      className="max-w-lg space-y-5"
      onSubmit={form.handleSubmit((values) => {
        change.mutate(
          { current_password: values.current_password, new_password: values.new_password },
          {
            onSuccess: (data) => {
              notify(data.message ?? 'Password changed.');
              form.reset();
            },
            onError: (error) => {
              applyServerErrors(error, form.setError, ['current_password', 'new_password']);
            },
          },
        );
      })}
    >
      {change.isError && <Alert tone="danger" title={errorMessage(change.error)} />}
      <FormField label="Current password" error={errors.current_password?.message}>
        <Input
          type="password"
          autoComplete="current-password"
          {...form.register('current_password')}
        />
      </FormField>
      <FormField
        label="New password"
        hint="At least 10 characters."
        error={errors.new_password?.message}
      >
        <Input type="password" autoComplete="new-password" {...form.register('new_password')} />
      </FormField>
      <FormField label="Repeat new password" error={errors.confirm?.message}>
        <Input type="password" autoComplete="new-password" {...form.register('confirm')} />
      </FormField>
      <Button type="submit" loading={change.isPending}>
        Change password
      </Button>
    </form>
  );
}

export function SecurityPage() {
  const sessions = useSessions();
  const revoke = useRevokeSession();
  const logout = useLogout();
  const { notify } = useToast();

  return (
    <>
      <PageMeta title="Sign-in & security" path="/account/security" noindex />
      <div className="space-y-14">
        <AccountSection
          title="Password"
          description="Changing your password signs you out on your other devices."
        >
          <ChangePasswordForm />
        </AccountSection>

        <AccountSection
          title="Signed-in devices"
          description="Sign out any device you don’t recognise, then change your password."
          action={
            <Button
              variant="secondary"
              size="sm"
              loading={logout.isPending}
              onClick={() => {
                logout.mutate(
                  { all: true, redirectTo: '/login' },
                  {
                    onSettled: () => {
                      notify('Signed out on all devices.', 'info');
                    },
                  },
                );
              }}
            >
              Sign out everywhere
            </Button>
          }
        >
          {sessions.isPending ? (
            <Skeleton className="h-32" />
          ) : sessions.isError ? (
            <ErrorState error={sessions.error} onRetry={() => void sessions.refetch()} />
          ) : (
            <ul className="divide-y divide-line rounded-md border border-line bg-surface">
              {sessions.data.map((session) => (
                <li key={session.id} className="flex flex-wrap items-center gap-4 p-4">
                  <Monitor className="size-5 text-ink-muted" strokeWidth={1.5} aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {session.device}
                      {session.current && (
                        <Badge tone="success" className="ml-2">
                          This device
                        </Badge>
                      )}
                    </p>
                    <p className="text-sm text-ink-muted">
                      Last active {formatDateTime(session.last_used_at)}
                      {session.ip_address ? ` · ${session.ip_address}` : ''}
                    </p>
                  </div>
                  {!session.current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={revoke.isPending && revoke.variables === session.id}
                      onClick={() => {
                        revoke.mutate(session.id, {
                          onSuccess: () => {
                            notify('Device signed out.', 'info');
                          },
                        });
                      }}
                    >
                      Sign out
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </AccountSection>
      </div>
    </>
  );
}

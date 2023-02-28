from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page

from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm


NUM_OF_PAGE = 10
CACHE_TIME = 20


def paginate(posts, request):
    paginator = Paginator(posts, NUM_OF_PAGE, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(CACHE_TIME, key_prefix='index_page')
def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()
    context = {
        'page_obj': paginate(posts, request),
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    context = {
        'group': group,
        'page_obj': paginate(posts, request),
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    following = (request.user.is_authenticated
                 and Follow.objects.filter(
                     user=request.user,
                     author=author).exists()
                 )
    context = {
        'posts': posts,
        'author': author,
        'page_obj': paginate(posts, request),
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.select_related('author')
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)
    context = {
        'form': form
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post_id = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post_id
    )
    context = {
        'form': form,
        'is_edit': True,
    }
    if request.user != post_id.author:
        return redirect('posts:post_detail', post_id=post_id.pk)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id.pk)
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginate = Paginator(posts, NUM_OF_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginate.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'follow': True
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user:
        Follow.objects.get_or_create(user=user, author=author)
        return redirect('posts:profile', str(user))
    return redirect('posts:profile', str(user))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    follow_for_delete = Follow.objects.filter(
        user=user,
        author=author
    )
    follow_for_delete.delete()
    return render(request, 'posts/index.html')

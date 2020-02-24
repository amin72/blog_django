from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from taggit.models import Tag
from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        tag_slug = self.request.GET.get('tag_slug')
        if tag_slug:
            tag = get_object_or_404(Tag, slug=tag_slug)
            qs = qs.filter(tags__in=[tag])
        return qs



def post_detail(request, year, month, day, slug):
    post = get_object_or_404(Post, slug=slug,
        status='published',
        publish__year=year,
        publish__month=month,
        publish__day=day)

    # list of active comments for this post
    comments = post.comments.filter(active=True)
    new_comment = None

    if request.method == 'POST':
        # a comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
            messages.info(request, 'Your comment has been added.')
            return redirect(post.get_absolute_url())

    # list of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)

    similar_posts = Post.published.filter(tags__in=post_tags_ids) \
        .exclude(id=post.id)

    similar_posts = similar_posts.annotate(same_tags=Count('tags')) \
        .order_by('-same_tags', '-publish')[:4]

    comment_form = CommentForm()
    context = {
        'post': post,
        'comments': comments,
        'new_comment': new_comment,
        'comment_form': comment_form,
        'similar_posts': similar_posts,
    }
    return render(request, 'blog/post/detail.html', context)



def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())

            subject = "{} ({}) recommends you reading {}".format(
                cd['name'], cd['email'], post.title)

            message = 'Read "{}" at {}\n\n'.format(post.title, post_url)

            if cd['comments']:
                message += '{}\'s comments: {}'.format(cd['name'],
                    cd['comments'])

            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            sent = True

    form = EmailPostForm()
    context = {
        'post': post,
        'form': form,
        'sent': sent,
    }
    return render(request, 'blog/post/share.html', context)



def post_search(request):
    form = SearchForm()
    query = None
    results = []

    # q is search query
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']

            search_vector = SearchVector('title', 'body')
            search_query = SearchQuery(query)

            results = Post.objects.annotate(
                search=search_query,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query).order_by('-rank')

    context = {'form': form, 'query': query, 'results': results}
    return render(request, 'blog/post/search.html', context)
